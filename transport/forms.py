from django import forms
from .models import Feedback, Route, Trip

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['route', 'trip', 'category', 'description']
        widgets = {
            'route': forms.Select(attrs={'class': 'form-control'}),
            'trip': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'route': 'Route (optional)',
            'trip': 'Trip (optional)',
            'category': 'Category',
            'description': 'Describe the issue or feedback',
        }