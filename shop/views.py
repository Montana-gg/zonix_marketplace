from django.shortcuts import render, get_object_or_404, redirect  # Добавили redirect сюда
from django.db.models import Avg
from .models import Category, Product, Review
from .forms import ReviewForm
from cart.forms import CartAddProductForm
from django.http import JsonResponse
from .models import Favorite
from django.contrib.auth.decorators import login_required



def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.filter(parent=None)

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

    # НОВОЕ: Получаем ID всех товаров, которые пользователь уже лайкнул
    favorite_product_ids = []
    if request.user.is_authenticated:
        favorite_product_ids = request.user.favorites.values_list('product_id', flat=True)

    cart_product_form = CartAddProductForm()
    return render(request, 'shop/product/list.html', {
        'category': category,
        'categories': categories,
        'products': products,
        'cart_product_form': cart_product_form,
        'query': query,
        'favorite_product_ids': favorite_product_ids  # Передаем в шаблон
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


@login_required  # Лайкать могут только авторизованные
def toggle_favorite(request, product_id):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        # Ищем, есть ли уже этот товар в избранном у пользователя
        favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)

        if not created:
            # Если запись уже была — значит пользователь кликнул, чтобы УДАЛИТЬ из избранного
            favorite.delete()
            status = 'removed'
        else:
            # Если записи не было — мы её только что создали (ДОБАВИЛИ)
            status = 'added'

        return JsonResponse({'status': status})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def favorite_list(request):
    # Получаем все объекты Favorite для текущего пользователя
    # и сразу подгружаем связанные товары (select_related), чтобы бд работала быстро
    favorites = Favorite.objects.filter(user=request.user).select_related('product')

    # Достаем чистый список товаров из объектов Favorite
    products = [fav.product for fav in favorites]

    return render(request, 'shop/product/favorites.html', {'products': products})