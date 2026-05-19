from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import OrderItem
from .forms import OrderCreateForm
from cart.cart import Cart


# orders/views.py
@login_required
def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            # commit=False позволяет создать объект, но не сохранять его сразу в БД
            order = form.save(commit=False)

            # Привязываем текущего авторизованного пользователя к заказу
            order.user = request.user

            # Теперь сохраняем заказ в базу данных
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
            return render(request, 'orders/order/created.html', {'order': order})
    else:
        form = OrderCreateForm()
    return render(request, 'orders/order/create.html', {'cart': cart, 'form': form})