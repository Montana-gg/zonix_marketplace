from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
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

    # Проверяем флаг перезаписи количества
    override_quantity = request.POST.get('override_quantity') == 'True' or request.POST.get('override') == 'True'

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

    # Получаем размер, чтобы удалить конкретную позицию товара
    size = request.POST.get('size', None)
    cart.remove(product, size=size)

    return redirect('cart:cart_detail')

def clear_session_cart(request):
    if 'cart' in request.session:
        del request.session['cart']
        request.session.modified = True
    return redirect('shop:product_list')