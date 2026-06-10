from decimal import Decimal
from shop.models import Product


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False, size=None):
        """
        Добавить товар в корзину или обновить его количество.
        """
        product_id = str(product.id)

        if size and size != '':
            item_key = f"{product_id}_{size}"
        else:
            item_key = product_id

        if item_key not in self.cart:
            self.cart[item_key] = {
                'product_id': int(product_id),  # ИСПРАВЛЕНО: Сохраняем ID, чтобы __iter__ его нашёл!
                'quantity': 0,
                'price': str(product.price),
                'size': size if (size and size != '') else None
            }

        if override_quantity:
            self.cart[item_key]['quantity'] = quantity
        else:
            self.cart[item_key]['quantity'] += quantity

        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, product, size=None):
        """
        Удаление товара из корзины.
        """
        product_id = str(product.id)

        if size and size != '':
            item_key = f"{product_id}_{size}"
        else:
            item_key = product_id

        if item_key in self.cart:
            del self.cart[item_key]
            self.save()

    def __iter__(self):
        """
        Перебор элементов в корзине и получение продуктов из базы данных.
        """
        # ИСПРАВЛЕНО: Достаем ID товаров безопасно
        product_ids = [item['product_id'] for item in self.cart.values() if 'product_id' in item]
        products = Product.objects.filter(id__in=product_ids)

        # Делаем копию корзины, чтобы не портить исходные сессионные данные при расчете total_price
        cart = self.cart.copy()

        for item_key, item in cart.items():
            if 'product_id' not in item:
                continue

            product = next((p for p in products if p.id == item['product_id']), None)
            if not product:
                continue

            item['product'] = product
            item['price'] = Decimal(item['price'])  # ИСПРАВЛЕНО: Лучше использовать Decimal для цен вместо float
            item['total_price'] = item['price'] * item['quantity']
            item['size'] = item.get('size', None)

            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        del self.session['cart']
        self.save()