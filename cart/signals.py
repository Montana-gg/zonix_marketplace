from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .cart import Cart


@receiver(user_logged_in)
def merge_saved_cart_on_login(sender, request, user, **kwargs):
    """
    При входе пользователя объединяем то, что он успел накидать
    в корзину как гость (сессия), с тем, что было сохранено за ним
    в БД с прошлого раза.
    """
    cart = Cart(request)
    cart.load_saved_cart()
