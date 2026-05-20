from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.Select(choices=[(i, f"{i} ★") for i in range(5, 0, -1)], attrs={'class': 'form-select rounded-3'}),
            'text': forms.Textarea(attrs={'class': 'form-control rounded-3', 'rows': 3, 'placeholder': 'Поделитесь впечатлениями о товаре...'}),
        }