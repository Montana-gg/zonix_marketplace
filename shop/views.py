from django.shortcuts import render, get_object_or_404, redirect  # Добавили redirect сюда
from django.db.models import Avg
from .models import Category, Product, Review
from .forms import ReviewForm
from cart.forms import CartAddProductForm


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.filter(parent=None)

    # Используем annotate, чтобы Django сам посчитал средний рейтинг для каждого товара
    products = Product.objects.filter(available=True).annotate(
        average_rating=Avg('reviews__rating')
    )

    # ПОИСК: если в URL есть ?query=...
    query = request.GET.get('query')
    if query:
        products = products.filter(name__icontains=query)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        category_ids = [category.id] + list(category.children.values_list('id', flat=True))
        products = products.filter(category_id__in=category_ids)

    cart_product_form = CartAddProductForm()
    return render(request, 'shop/product/list.html', {
        'category': category,
        'categories': categories,
        'products': products,
        'cart_product_form': cart_product_form,
        'query': query
    })

def product_detail(request, id, slug):  # Убрали @login_required, чтобы карточка была доступна всем
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    cart_product_form = CartAddProductForm()

    # Получаем все отзывы к этому конкретному товару
    reviews = product.reviews.all()

    # Считаем средний рейтинг товара (округляем до 1 знака после запятой)
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    if average_rating:
        average_rating = round(average_rating, 1)

    # Обработка отправки отзыва
    if request.method == 'POST' and request.user.is_authenticated:
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            # Перенаправляем на ту же страницу, чтобы сбросить POST-данные
            return redirect('shop:product_detail', id=product.id, slug=product.slug)
    else:
        review_form = ReviewForm()

    context = {
        'product': product,
        'cart_product_form': cart_product_form,
        'reviews': reviews,
        'review_form': review_form,
        'average_rating': average_rating
    }
    return render(request, 'shop/product/detail.html', context)