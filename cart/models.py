from django.conf import settings
from django.db import models

from shop.models import Product


class CartItem(models.Model):
    """
    Персистентная копия корзины для авторизованного пользователя.

    Пока пользователь на сайте, основная работа с корзиной идёт через
    сессию (см. cart/cart.py) — это быстро и не требует лишних запросов
    к БД на каждый клик. Но при каждом изменении сессионной корзины она
    синхронизируется сюда, чтобы пользователь не терял корзину при входе
    с другого устройства или после истечения сессии.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name='Пользователь',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Товар',
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')
    size = models.CharField(max_length=10, blank=True, null=True, verbose_name='Размер')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена на момент добавления')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлено')

    class Meta:
        unique_together = ('user', 'product', 'size')
        verbose_name = 'Товар в сохранённой корзине'
        verbose_name_plural = 'Сохранённые корзины'

    def __str__(self):
        return f'{self.user.username} — {self.product.name} x{self.quantity}'