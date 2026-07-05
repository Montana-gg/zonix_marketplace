from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages
from shop.models import Product
from .cart import Cart


@login_required
@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)

    # Считываем переданное количество и размер из формы
    quantity = int(request.POST.get('quantity', 1))
    size = request.POST.get('size', None)  # Получаем размер (M, L, XL...)

    # ИСПРАВЛЕНИЕ: Если размер пришел пустой строкой, принудительно делаем его None
    if size == '':
        size = None

    # Проверяем флаг перезаписи количества
    override_quantity = request.POST.get('override_quantity') == 'True' or request.POST.get('override') == 'True'

    # Валидация остатков на складе: считаем, сколько этого товара
    # УЖЕ лежит в корзине (если не перезаписываем количество, а добавляем ещё),
    # и не даём запросить больше, чем реально есть в наличии.
    already_in_cart = 0
    item_key = f"{product_id}_{size}" if size else str(product_id)
    if not override_quantity and item_key in cart.cart:
        already_in_cart = cart.cart[item_key]['quantity']

    requested_total = quantity if override_quantity else already_in_cart + quantity

    if requested_total > product.stock:
        messages.error(
            request,
            f'На складе доступно только {product.stock} шт. товара «{product.name}». '
            f'Уменьшите количество.'
        )
        return redirect('cart:cart_detail')

    # Передаем размер в корзину
    cart.add(product=product,
             quantity=quantity,
             override_quantity=override_quantity,
             size=size)

    return redirect('cart:cart_detail')


def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart/detail.html', {'cart': cart})


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)

    # Получаем размер, прилетевший из формы
    size = request.POST.get('size', None)

    # ИСПРАВЛЕНИЕ: Если размер пришел пустой строкой (как у ноутбука), принудительно делаем его None
    if size == '':
        size = None

    cart.remove(product, size=size)

    return redirect('cart:cart_detail')


def clear_session_cart(request):
    if 'cart' in request.session:
        del request.session['cart']
        request.session.modified = True
    return redirect('shop:product_list')