from django.contrib import admin
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Добавляем status в список отображения и в редактируемые поля
    list_display = ['id', 'first_name', 'last_name', 'email', 'status', 'paid', 'created']
    list_editable = ['status', 'paid'] # Это позволит менять статус прямо в таблице!
    list_filter = ['status', 'paid', 'created', 'updated']
