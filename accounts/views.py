from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms

def signUp (request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            redirect('login')
            messages.success(request, ('Registration successful!'))
    else:

        form = UserCreationForm()

        context= {
            'form':form,
            'title': 'Register'
        }

    return render(request, 'registration/register.html', context)


class UserEditForm(forms.ModelForm):
     class Meta:
        model = User
        fields = ['username', 'email']  # Add other fields as necessary
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        }

def profile(request):
    user = request.user  # Get the currently logged-in user

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()  # Save the updated user information
            return redirect('profile')  # Redirect to the profile page after saving
    else:
        form = UserEditForm(instance=user)  # Pre-fill the form with the user's current information

    context = {
        'form': form,
    }
    return render(request, 'profile/profile.html', context)