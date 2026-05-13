from django.shortcuts import render, get_object_or_404
from .models import Category, Product
from cart.forms import CartAddProductForm
from django.contrib.auth.decorators import login_required # Добавь импорт


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.filter(parent=None)
    products = Product.objects.filter(available=True)

    # ПОИСК: если в URL есть ?query=...
    query = request.GET.get('query')
    if query:
        products = products.filter(name__icontains=query)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        # Находим саму категорию и всех её "детей"
        category_ids = [category.id] + list(category.children.values_list('id', flat=True))
        # Фильтруем товары, которые входят в этот список ID
        products = products.filter(category_id__in=category_ids)

    cart_product_form = CartAddProductForm()
    return render(request, 'shop/product/list.html', {
        'category': category,
        'categories': categories,
        'products': products,
        'cart_product_form': cart_product_form,
        'query': query
    })

@login_required
def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)


    cart_product_form = CartAddProductForm()

    return render(request,
                  'shop/product/detail.html',
                  {'product': product,
                   'cart_product_form': cart_product_form})  # И здесь передаем