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

    # Получаем количество из POST-запроса
    quantity = int(request.POST.get('quantity', 1))

    # Приводим override к булевому значению (True/False)
    override_raw = request.POST.get('override', 'False')
    override = override_raw in ['True', 'true', True, 1]

    # Добавляем товар в корзину ОДИН раз
    cart.add(product=product, quantity=quantity, override_quantity=override)

    # Если это AJAX-запрос от JavaScript
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Безопасно считаем сумму всех товаров напрямую из словаря сессии cart.cart
        # Это гарантирует, что отсутствие методов __len__ или __iter__ в классе ничего не сломает
        total_items = sum(int(item['quantity']) for item in cart.cart.values())

        return JsonResponse({
            'status': 'success',
            'cart_total_items': total_items,
            'cart_total_price': str(cart.get_total_price())
        })

    # Обычный редирект для старых кнопок (если AJAX отключен)
    return redirect('cart:cart_detail')

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart/detail.html', {'cart': cart})

@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product) # Вызываем метод из класса Cart
    return redirect('cart:cart_detail')