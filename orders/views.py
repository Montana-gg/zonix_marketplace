from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem
from .forms import OrderCreateForm
from cart.cart import Cart


@login_required
def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()

            for item in cart:
                product = item['product']
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    price=item['price'],
                    quantity=item['quantity']
                )
                product.stock -= item['quantity']
                product.save()

            cart.clear()
            # ВМЕСТО старого рендера создаем редирект на страницу оплаты
            return redirect('orders:order_payment', order_id=order.id)
    else:
        form = OrderCreateForm()
    return render(request, 'orders/order/create.html', {'cart': cart, 'form': form})


@login_required
def order_payment(request, order_id):
    # Получаем заказ, проверяя, что он принадлежит именно текущему пользователю
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        # Если пользователь нажал "Оплатить"
        order.paid = True
        order.status = 'Оплачен'  # Убедись, что в твоем Choices модели Order есть статус 'Оплачен'
        order.save()
        # После успешной оплаты отправляем на страницу "Спасибо за заказ"
        return render(request, 'orders/order/created.html', {'order': order})

    return render(request, 'orders/order/payment.html', {'order': order})