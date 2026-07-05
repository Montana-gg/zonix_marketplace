from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Category, Favorite, Product, Review


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Электроника', slug='electronics')

    def test_get_sizes_list_parses_comma_separated_string(self):
        product = Product.objects.create(
            category=self.category,
            name='Футболка',
            slug='futbolka',
            price=Decimal('500.00'),
            sizes='S, M, L',
        )
        self.assertEqual(product.get_sizes_list(), ['S', 'M', 'L'])

    def test_get_sizes_list_returns_empty_list_when_no_sizes(self):
        product = Product.objects.create(
            category=self.category,
            name='Ноутбук',
            slug='noutbuk',
            price=Decimal('45000.00'),
        )
        self.assertEqual(product.get_sizes_list(), [])

    def test_product_str_returns_name(self):
        product = Product.objects.create(
            category=self.category,
            name='iPhone 15',
            slug='iphone-15',
            price=Decimal('80000.00'),
        )
        self.assertEqual(str(product), 'iPhone 15')


class CategoryModelTests(TestCase):
    def test_category_can_have_children(self):
        parent = Category.objects.create(name='Одежда', slug='clothes')
        child = Category.objects.create(name='Футболки', slug='tshirts', parent=parent)

        self.assertIn(child, parent.children.all())

    def test_category_slug_must_be_unique(self):
        Category.objects.create(name='Одежда', slug='clothes')
        with self.assertRaises(Exception):
            # unique=True на slug должно кинуть IntegrityError на уровне БД
            Category.objects.create(name='Другая одежда', slug='clothes')


class ReviewModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Обувь', slug='shoes')
        self.product = Product.objects.create(
            category=self.category, name='Кроссовки', slug='krossovki',
            price=Decimal('3000.00'),
        )
        self.user = User.objects.create_user(username='buyer', password='testpass123')

    def test_rating_within_valid_range_passes_validation(self):
        review = Review(product=self.product, user=self.user, text='Отлично', rating=5)
        review.full_clean()  # не должно кинуть исключение

    def test_rating_above_five_fails_validation(self):
        review = Review(product=self.product, user=self.user, text='Слишком хорошо', rating=6)
        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_rating_below_one_fails_validation(self):
        review = Review(product=self.product, user=self.user, text='Плохо', rating=0)
        with self.assertRaises(ValidationError):
            review.full_clean()


class FavoriteModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Техника', slug='tech')
        self.product = Product.objects.create(
            category=self.category, name='Фен', slug='fen', price=Decimal('1500.00'),
        )
        self.user = User.objects.create_user(username='fan', password='testpass123')

    def test_user_cannot_favorite_same_product_twice(self):
        Favorite.objects.create(user=self.user, product=self.product)
        with self.assertRaises(Exception):
            # unique_together должно помешать дублю
            Favorite.objects.create(user=self.user, product=self.product)


class ProductListViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Одежда', slug='clothes')
        self.available_product = Product.objects.create(
            category=self.category, name='Куртка', slug='kurtka',
            price=Decimal('5000.00'), available=True,
        )
        self.hidden_product = Product.objects.create(
            category=self.category, name='Снятая с продажи вещь', slug='hidden',
            price=Decimal('100.00'), available=False,
        )

    def test_product_list_shows_only_available_products(self):
        response = self.client.get(reverse('shop:product_list'))

        products = list(response.context['products'])
        self.assertIn(self.available_product, products)
        self.assertNotIn(self.hidden_product, products)

    def test_search_query_filters_by_name(self):
        Product.objects.create(
            category=self.category, name='Ботинки', slug='botinki',
            price=Decimal('2000.00'), available=True,
        )

        response = self.client.get(reverse('shop:product_list'), {'query': 'куртка'})

        products = list(response.context['products'])
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0], self.available_product)

    def test_category_filter_includes_child_categories(self):
        child_category = Category.objects.create(name='Куртки', slug='jackets', parent=self.category)
        product_in_child = Product.objects.create(
            category=child_category, name='Зимняя куртка', slug='zimnaya-kurtka',
            price=Decimal('8000.00'), available=True,
        )

        response = self.client.get(
            reverse('shop:product_list_by_category', args=[self.category.slug])
        )

        products = list(response.context['products'])
        self.assertIn(product_in_child, products)
        self.assertIn(self.available_product, products)


class ToggleFavoriteViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Спорт', slug='sport')
        self.product = Product.objects.create(
            category=self.category, name='Мяч', slug='myach', price=Decimal('800.00'),
        )
        self.user = User.objects.create_user(username='sporty', password='testpass123')

    def test_anonymous_user_cannot_toggle_favorite(self):
        response = self.client.post(
            reverse('shop:toggle_favorite', args=[self.product.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        # login_required должен увести на страницу логина, а не выполнить действие
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(Favorite.objects.count(), 0)

    def test_authenticated_user_can_add_and_remove_favorite(self):
        self.client.login(username='sporty', password='testpass123')
        url = reverse('shop:toggle_favorite', args=[self.product.id])

        response_add = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_add.json()['status'], 'added')
        self.assertEqual(Favorite.objects.count(), 1)

        response_remove = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_remove.json()['status'], 'removed')
        self.assertEqual(Favorite.objects.count(), 0)

    def test_toggle_favorite_without_ajax_header_returns_error(self):
        self.client.login(username='sporty', password='testpass123')
        response = self.client.post(reverse('shop:toggle_favorite', args=[self.product.id]))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
