# cart/forms.py
from django import forms

PRODUCT_QUANTITY_CHOICES = [(i, str(i)) for i in range(1, 21)]

class CartAddProductForm(forms.Form):
    # Изменяем ChoiceField на IntegerField, чтобы принимать любые числа из инпута
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control text-center'})
    )
    override = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)