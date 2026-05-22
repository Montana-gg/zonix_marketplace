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
        # Формируем уникальный ключ для корзины (например: "5_M" или "5_None")
        item_id = f"{product.id}_{size}" if size else f"{product.id}_None"

        if item_id not in self.cart:
            self.cart[item_id] = {
                'quantity': 0,
                'price': str(product.price),
                'product_id': product.id,
                'size': size  # СОХРАНЯЕМ ВЫБРАННЫЙ РАЗМЕР В СЕССИЮ
            }

        if override_quantity:
            self.cart[item_id]['quantity'] = quantity
        else:
            self.cart[item_id]['quantity'] += quantity

        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, product, size=None):
        item_key = str(product.id)
        if size:
            item_key = f"{product.id}_{size}"
        if item_key in self.cart:
            del self.cart[item_key]
            self.save()

    def __iter__(self):
        product_ids = [item['product_id'] for item in self.cart.values() if 'product_id' in item]
        products = Product.objects.filter(id__in=product_ids)

        cart = self.cart.copy()

        for item_key, item in cart.items():
            if 'product_id' not in item:
                continue

            product = next((p for p in products if p.id == item['product_id']), None)
            if not product:
                continue

            item['product'] = product
            item['price'] = float(item['price'])
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