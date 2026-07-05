from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from shop.models import Category, Product
from .models import Order, OrderItem


class OrderModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='client', password='testpass123')
        self.category = Category.objects.create(name='Одежда', slug='clothes')
        self.product = Product.objects.create(
            category=self.category, name='Куртка', slug='kurtka',
            price=Decimal('5000.00'), stock=10,
        )
        self.order = Order.objects.create(
            user=self.user, first_name='Батырбек', last_name='Таджибоев',
            email='test@example.com', address='ул. Тестовая, 1',
            postal_code='720000', city='Бишкек',
        )

    def test_order_str_includes_id(self):
        self.assertEqual(str(self.order), f'Order {self.order.id}')

    def test_default_status_is_new(self):
        self.assertEqual(self.order.status, 'new')
        self.assertFalse(self.order.paid)

    def test_get_total_cost_sums_all_order_items(self):
        OrderItem.objects.create(order=self.order, product=self.product, price=Decimal('5000.00'), quantity=2)
        OrderItem.objects.create(order=self.order, product=self.product, price=Decimal('5000.00'), quantity=1)

        self.assertEqual(self.order.get_total_cost(), Decimal('15000.00'))

    def test_get_total_cost_is_zero_for_empty_order(self):
        self.assertEqual(self.order.get_total_cost(), 0)


class OrderItemModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='client2', password='testpass123')
        self.category = Category.objects.create(name='Обувь', slug='shoes')
        self.product = Product.objects.create(
            category=self.category, name='Кроссовки', slug='krossovki',
            price=Decimal('3000.00'), stock=5,
        )
        self.order = Order.objects.create(
            user=self.user, first_name='А', last_name='Б',
            email='a@example.com', address='адрес', postal_code='000000', city='Бишкек',
        )

    def test_get_cost_multiplies_price_by_quantity(self):
        item = OrderItem.objects.create(order=self.order, product=self.product, price=Decimal('3000.00'), quantity=3)
        self.assertEqual(item.get_cost(), Decimal('9000.00'))


class OrderCreateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='testpass123')
        self.category = Category.objects.create(name='Техника', slug='tech')
        self.product = Product.objects.create(
            category=self.category, name='Наушники', slug='naushniki',
            price=Decimal('2000.00'), stock=5,
        )

    def _add_product_to_session_cart(self):
        session = self.client.session
        session['cart'] = {
            str(self.product.id): {
                'product_id': self.product.id,
                'quantity': 2,
                'price': str(self.product.price),
                'size': None,
            }
        }
        session.save()

    def test_anonymous_user_redirected_from_order_create(self):
        response = self.client.get(reverse('orders:order_create'))
        self.assertEqual(response.status_code, 302)

    def test_order_create_creates_order_items_and_reduces_stock(self):
        self.client.login(username='buyer', password='testpass123')
        self._add_product_to_session_cart()

        response = self.client.post(reverse('orders:order_create'), {
            'first_name': 'Батырбек',
            'last_name': 'Таджибоев',
            'email': 'buyer@example.com',
            'address': 'ул. Примерная, 5',
            'postal_code': '720000',
            'city': 'Бишкек',
        })

        self.assertEqual(response.status_code, 200)
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().quantity, 2)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)  # было 5, купили 2

    def test_order_create_clears_the_cart(self):
        self.client.login(username='buyer', password='testpass123')
        self._add_product_to_session_cart()

        self.client.post(reverse('orders:order_create'), {
            'first_name': 'Батырбек', 'last_name': 'Таджибоев',
            'email': 'buyer@example.com', 'address': 'ул. Примерная, 5',
            'postal_code': '720000', 'city': 'Бишкек',
        })

        self.assertNotIn('cart', self.client.session)


class OrderPaymentViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='payer', password='testpass123')
        self.order = Order.objects.create(
            user=self.user, first_name='А', last_name='Б',
            email='a@example.com', address='адрес', postal_code='000000', city='Бишкек',
        )

    def test_payment_sets_valid_status_value_not_display_label(self):
        """
        Регрессионный тест на баг: во views.py статус записывался как
        русская подпись 'Оплачен' вместо валидного ключа 'paid' из
        STATUS_CHOICES. Проверяем, что в базе теперь хранится 'paid'.
        """
        self.client.login(username='payer', password='testpass123')

        self.client.post(reverse('orders:order_payment', args=[self.order.id]))

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'paid')
        self.assertTrue(self.order.paid)

    def test_other_users_order_returns_404(self):
        other_user = User.objects.create_user(username='stranger', password='testpass123')
        self.client.login(username='stranger', password='testpass123')

        response = self.client.get(reverse('orders:order_payment', args=[self.order.id]))
        self.assertEqual(response.status_code, 404)


class HideOrderViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='hider', password='testpass123')
        self.order = Order.objects.create(
            user=self.user, first_name='А', last_name='Б',
            email='a@example.com', address='адрес', postal_code='000000', city='Бишкек',
        )

    def test_hide_order_sets_flag_false(self):
        self.client.login(username='hider', password='testpass123')
        self.client.post(reverse('orders:hide_order', args=[self.order.id]))

        self.order.refresh_from_db()
        self.assertFalse(self.order.is_visible_to_user)

    def test_cannot_hide_someone_elses_order(self):
        other_user = User.objects.create_user(username='intruder', password='testpass123')
        self.client.login(username='intruder', password='testpass123')

        response = self.client.post(reverse('orders:hide_order', args=[self.order.id]))
        self.assertEqual(response.status_code, 404)


class OrderCreateStockValidationTests(TestCase):
    """
    Тест на защиту от гонки: товар успели купить между добавлением
    в корзину и оформлением заказа - заказ не должен пройти.
    """

    def setUp(self):
        self.user = User.objects.create_user(username='racer', password='testpass123')
        self.category = Category.objects.create(name='Электроника', slug='electronics-race')
        self.product = Product.objects.create(
            category=self.category, name='Мышка', slug='myshka',
            price=Decimal('800.00'), stock=2,
        )
        self.client.login(username='racer', password='testpass123')

        session = self.client.session
        session['cart'] = {
            str(self.product.id): {
                'product_id': self.product.id,
                'quantity': 2,
                'price': str(self.product.price),
                'size': None,
            }
        }
        session.save()

    def test_order_rejected_if_stock_dropped_below_cart_quantity(self):
        # Имитация: пока товар лежал в корзине, остаток на складе упал до 1
        self.product.stock = 1
        self.product.save()

        response = self.client.post(reverse('orders:order_create'), {
            'first_name': 'А', 'last_name': 'Б', 'email': 'a@example.com',
            'address': 'адрес', 'postal_code': '000000', 'city': 'Бишкек',
        })

        self.assertRedirects(response, reverse('cart:cart_detail'))
        self.assertEqual(Order.objects.filter(user=self.user).count(), 0)

        # Остаток на складе не должен был измениться - заказ не создавался
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
