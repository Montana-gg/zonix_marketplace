from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse

from shop.models import Category, Product
from .cart import Cart
from .models import CartItem


class CartTestCase(TestCase):
    """
    Тесты для класса Cart (cart/cart.py).

    Корзина хранится в сессии, поэтому вместо HTTP-запросов через клиент
    используем RequestFactory + SessionMiddleware, чтобы получить
    request с реальным session-объектом и тестировать Cart напрямую.
    """

    def setUp(self):
        self.category = Category.objects.create(name='Одежда', slug='clothes')

        self.product_shirt = Product.objects.create(
            category=self.category,
            name='Футболка',
            slug='futbolka',
            price=Decimal('500.00'),
            stock=10,
            sizes='S,M,L',
        )
        self.product_laptop = Product.objects.create(
            category=self.category,
            name='Ноутбук',
            slug='noutbuk',
            price=Decimal('45000.00'),
            stock=3,
        )

        self.request = self._build_request_with_session()
        self.cart = Cart(self.request)

    def _build_request_with_session(self):
        """Создаёт request с настоящей рабочей сессией."""
        request = RequestFactory().get('/')
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        return request

    # --- Базовое добавление ---

    def test_add_product_creates_entry_in_session(self):
        self.cart.add(product=self.product_laptop, quantity=1)

        self.assertEqual(len(self.cart.cart), 1)
        item_key = str(self.product_laptop.id)
        self.assertIn(item_key, self.cart.cart)
        self.assertEqual(self.cart.cart[item_key]['quantity'], 1)

    def test_add_same_product_twice_increments_quantity(self):
        self.cart.add(product=self.product_laptop, quantity=1)
        self.cart.add(product=self.product_laptop, quantity=2)

        item_key = str(self.product_laptop.id)
        self.assertEqual(self.cart.cart[item_key]['quantity'], 3)

    def test_override_quantity_replaces_instead_of_adding(self):
        self.cart.add(product=self.product_laptop, quantity=2)
        self.cart.add(product=self.product_laptop, quantity=5, override_quantity=True)

        item_key = str(self.product_laptop.id)
        self.assertEqual(self.cart.cart[item_key]['quantity'], 5)

    # --- Работа с размерами (вариативные товары) ---

    def test_same_product_different_sizes_are_separate_items(self):
        self.cart.add(product=self.product_shirt, quantity=1, size='M')
        self.cart.add(product=self.product_shirt, quantity=1, size='L')

        self.assertEqual(len(self.cart.cart), 2)
        self.assertIn(f'{self.product_shirt.id}_M', self.cart.cart)
        self.assertIn(f'{self.product_shirt.id}_L', self.cart.cart)

    def test_product_without_size_uses_plain_id_as_key(self):
        self.cart.add(product=self.product_laptop, quantity=1, size='')

        self.assertIn(str(self.product_laptop.id), self.cart.cart)
        self.assertNotIn(f'{self.product_laptop.id}_', self.cart.cart)

    # --- Регрессионный тест на баг из резюме ---

    def test_product_id_is_always_saved_for_iteration(self):
        """
        Регрессионный тест на баг, из-за которого корзина "не видела"
        товары из базы: при добавлении не сохранялся product_id,
        и __iter__ не мог найти товар по id__in=product_ids.
        """
        self.cart.add(product=self.product_shirt, quantity=1, size='M')

        item_key = f'{self.product_shirt.id}_M'
        self.assertIn('product_id', self.cart.cart[item_key])
        self.assertEqual(self.cart.cart[item_key]['product_id'], self.product_shirt.id)

    def test_iter_yields_real_products_from_database(self):
        self.cart.add(product=self.product_shirt, quantity=2, size='M')
        self.cart.add(product=self.product_laptop, quantity=1)

        items = list(self.cart)

        self.assertEqual(len(items), 2)
        products_in_cart = {item['product'].id for item in items}
        self.assertEqual(products_in_cart, {self.product_shirt.id, self.product_laptop.id})

    def test_iter_skips_items_without_product_id(self):
        """
        Даже если в сессии окажется "битый" элемент без product_id
        (например, из старой версии корзины), __iter__ не должен падать.
        """
        self.cart.cart['broken_key'] = {'quantity': 1, 'price': '100.00'}
        self.cart.save()

        items = list(self.cart)

        self.assertEqual(items, [])

    def test_iter_calculates_total_price_per_item_as_decimal(self):
        self.cart.add(product=self.product_shirt, quantity=3, size='M')

        item = next(iter(self.cart))

        self.assertIsInstance(item['price'], Decimal)
        self.assertEqual(item['total_price'], Decimal('500.00') * 3)

    # --- Удаление ---

    def test_remove_product_deletes_it_from_cart(self):
        self.cart.add(product=self.product_laptop, quantity=1)
        self.cart.remove(self.product_laptop)

        self.assertEqual(len(self.cart.cart), 0)

    def test_remove_specific_size_does_not_affect_other_sizes(self):
        self.cart.add(product=self.product_shirt, quantity=1, size='M')
        self.cart.add(product=self.product_shirt, quantity=1, size='L')

        self.cart.remove(self.product_shirt, size='M')

        self.assertNotIn(f'{self.product_shirt.id}_M', self.cart.cart)
        self.assertIn(f'{self.product_shirt.id}_L', self.cart.cart)

    def test_remove_nonexistent_product_does_not_raise(self):
        # Товар не был добавлен - удаление не должно кидать исключение
        self.cart.remove(self.product_laptop)
        self.assertEqual(len(self.cart.cart), 0)

    # --- Подсчёты ---

    def test_len_returns_total_quantity_not_item_count(self):
        self.cart.add(product=self.product_shirt, quantity=2, size='M')
        self.cart.add(product=self.product_laptop, quantity=3)

        # 2 разные позиции в корзине, но суммарно 5 единиц товара
        self.assertEqual(len(self.cart), 5)

    def test_get_total_price_sums_all_items(self):
        self.cart.add(product=self.product_shirt, quantity=2, size='M')  # 500 * 2 = 1000
        self.cart.add(product=self.product_laptop, quantity=1)  # 45000 * 1 = 45000

        self.assertEqual(self.cart.get_total_price(), Decimal('46000.00'))

    def test_get_total_price_returns_decimal_not_float(self):
        self.cart.add(product=self.product_shirt, quantity=1, size='M')

        self.assertIsInstance(self.cart.get_total_price(), Decimal)

    # --- Очистка ---

    def test_clear_removes_cart_from_session(self):
        self.cart.add(product=self.product_laptop, quantity=1)
        self.cart.clear()

        self.assertNotIn('cart', self.request.session)


class AuthenticatedCartDbSyncTestCase(TestCase):
    """
    Тесты на сохранение корзины авторизованного пользователя в БД
    (модель CartItem) и восстановление её при следующем логине.
    """

    def setUp(self):
        self.category = Category.objects.create(name='Одежда', slug='clothes-db')
        self.product = Product.objects.create(
            category=self.category, name='Свитер', slug='sviter',
            price=Decimal('1200.00'), stock=10,
        )
        self.user = User.objects.create_user(username='dbcart', password='testpass123')

    def _build_authenticated_request(self):
        request = RequestFactory().get('/')
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        request.user = self.user
        return request

    def test_adding_product_creates_cart_item_in_db(self):
        request = self._build_authenticated_request()
        cart = Cart(request)

        cart.add(product=self.product, quantity=2, size='M')

        saved_items = CartItem.objects.filter(user=self.user)
        self.assertEqual(saved_items.count(), 1)
        self.assertEqual(saved_items.first().quantity, 2)
        self.assertEqual(saved_items.first().size, 'M')

    def test_saving_twice_does_not_duplicate_db_items(self):
        request = self._build_authenticated_request()
        cart = Cart(request)

        cart.add(product=self.product, quantity=1)
        cart.add(product=self.product, quantity=1)  # тот же товар, второй раз

        # В сессии одна позиция с quantity=2, а не два отдельных CartItem
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 1)
        self.assertEqual(CartItem.objects.get(user=self.user).quantity, 2)

    def test_removing_product_deletes_it_from_db_too(self):
        request = self._build_authenticated_request()
        cart = Cart(request)
        cart.add(product=self.product, quantity=1)

        cart.remove(self.product)

        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 0)

    def test_clear_removes_db_items_too(self):
        request = self._build_authenticated_request()
        cart = Cart(request)
        cart.add(product=self.product, quantity=1)

        cart.clear()

        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 0)

    def test_load_saved_cart_restores_items_into_new_session(self):
        """
        Имитация входа с нового устройства: в БД уже есть сохранённая
        корзина, а сессия - пустая. load_saved_cart() должен подтянуть
        товары в новую (пустую) сессионную корзину.
        """
        CartItem.objects.create(
            user=self.user, product=self.product, quantity=3,
            size=None, price=self.product.price,
        )

        request = self._build_authenticated_request()
        cart = Cart(request)
        self.assertEqual(len(cart), 0)  # сессия пустая, товар ещё не подгружен

        cart.load_saved_cart()

        self.assertEqual(len(cart), 3)
        item = next(iter(cart))
        self.assertEqual(item['product'], self.product)

    def test_load_saved_cart_merges_with_existing_guest_items(self):
        """
        Пользователь как гость добавил товар А, потом залогинился,
        а в БД у него уже был сохранён товар Б с прошлого раза.
        После merge в корзине должны быть оба товара.
        """
        other_product = Product.objects.create(
            category=self.category, name='Шарф', slug='sharf',
            price=Decimal('400.00'), stock=5,
        )
        CartItem.objects.create(
            user=self.user, product=other_product, quantity=1,
            size=None, price=other_product.price,
        )

        # Гостевая часть сессии: пользователь ещё НЕ залогинен,
        # поэтому add() пока не трогает БД (self.user is None).
        from django.contrib.auth.models import AnonymousUser

        request = RequestFactory().get('/')
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        request.user = AnonymousUser()

        guest_cart = Cart(request)
        guest_cart.add(product=self.product, quantity=1)

        # Пользователь логинится на этой же сессии (request.session сохраняется)
        request.user = self.user
        cart = Cart(request)
        cart.load_saved_cart()

        product_ids_in_cart = {item['product'].id for item in cart}
        self.assertEqual(product_ids_in_cart, {self.product.id, other_product.id})

    def test_anonymous_user_does_not_touch_database(self):
        """Для анонима корзина работает только в сессии, без записи в БД."""
        anon_request = RequestFactory().get('/')
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(anon_request)
        anon_request.session.save()

        from django.contrib.auth.models import AnonymousUser
        anon_request.user = AnonymousUser()

        cart = Cart(anon_request)
        cart.add(product=self.product, quantity=1)

        self.assertEqual(CartItem.objects.count(), 0)


class CartAddStockValidationViewTests(TestCase):
    """
    Тесты на валидацию: нельзя добавить в корзину больше товара,
    чем реально есть на складе (product.stock).
    """

    def setUp(self):
        self.category = Category.objects.create(name='Техника', slug='tech-stock')
        self.product = Product.objects.create(
            category=self.category, name='Клавиатура', slug='klaviatura',
            price=Decimal('2500.00'), stock=3,
        )
        self.user = User.objects.create_user(username='stockbuyer', password='testpass123')
        self.client.login(username='stockbuyer', password='testpass123')

    def test_can_add_quantity_within_stock(self):
        response = self.client.post(
            reverse('cart:cart_add', args=[self.product.id]),
            {'quantity': 3},
        )
        self.assertRedirects(response, reverse('cart:cart_detail'))
        session_cart = self.client.session['cart']
        self.assertEqual(session_cart[str(self.product.id)]['quantity'], 3)

    def test_cannot_add_more_than_available_stock(self):
        response = self.client.post(
            reverse('cart:cart_add', args=[self.product.id]),
            {'quantity': 5},  # на складе только 3
        )
        self.assertRedirects(response, reverse('cart:cart_detail'))
        # Товар не должен попасть в корзину
        session_cart = self.client.session.get('cart', {})
        self.assertNotIn(str(self.product.id), session_cart)

    def test_cannot_exceed_stock_by_adding_twice(self):
        self.client.post(reverse('cart:cart_add', args=[self.product.id]), {'quantity': 2})
        # Пытаемся добавить ещё 2 - в сумме 4, а на складе только 3
        response = self.client.post(
            reverse('cart:cart_add', args=[self.product.id]),
            {'quantity': 2},
        )

        session_cart = self.client.session['cart']
        # Количество должно остаться прежним (2), вторая попытка отклонена
        self.assertEqual(session_cart[str(self.product.id)]['quantity'], 2)

    def test_override_quantity_above_stock_is_rejected(self):
        response = self.client.post(
            reverse('cart:cart_add', args=[self.product.id]),
            {'quantity': 10, 'override_quantity': 'True'},
        )

        session_cart = self.client.session.get('cart', {})
        self.assertNotIn(str(self.product.id), session_cart)
