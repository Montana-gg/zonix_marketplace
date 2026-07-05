from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Order, OrderItem
from .forms import OrderCreateForm
from cart.cart import Cart


@login_required
@require_POST
def hide_order(request, order_id):
    # Ищем заказ текущего пользователя
    order = get_object_or_404(Order, id=order_id, user=request.user)

    order.is_visible_to_user = False
    order.save()

    # Возвращаем пользователя обратно на страницу профиля, откуда пришел запрос
    return redirect(request.META.get('HTTP_REFERER', '/accounts/profile/'))


@login_required
def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            # Финальная проверка остатков на складе перед оформлением.
            # Важно перепроверить прямо здесь, а не полагаться только на
            # проверку при добавлении в корзину: с момента добавления
            # остатки могли измениться (например, товар купил кто-то ещё).
            for item in cart:
                if item['quantity'] > item['product'].stock:
                    messages.error(
                        request,
                        f'К сожалению, товара «{item["product"].name}» осталось '
                        f'только {item["product"].stock} шт. Обновите корзину.'
                    )
                    return redirect('cart:cart_detail')

            order = form.save(commit=False)
            order.user = request.user
            order.save()

            for item in cart:
                # 1. Создаем позицию в заказе
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity'],
                    size=item.get('size')  # Передаем размер из корзины в БД заказа
                )

                # 2. УМЕНЬШАЕМ КОЛИЧЕСТВО НА СКЛАДЕ:
                product = item['product']
                product.stock -= item['quantity']
                product.save()  # Сохраняем обновленный склад товара в БД

            cart.clear()
            return render(request, 'orders/order/created.html', {'order': order})
    else:
        form = OrderCreateForm()
    return render(request, 'orders/order/create.html', {'cart': cart, 'form': form})

@login_required
def order_payment(request, order_id):
    # Получаем заказ, проверяя, что он принадлежит именно текущему пользователю
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        order.paid = True
        order.status = 'paid'
        order.save()
        # После успешной оплаты отправляем на страницу "Спасибо за заказ"
        return render(request, 'orders/order/created.html', {'order': order})

    return render(request, 'orders/order/payment.html', {'order': order})