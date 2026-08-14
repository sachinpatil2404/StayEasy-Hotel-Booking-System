from django import forms
from .models import Booking
from django.forms.widgets import DateInput
from django.contrib.auth.models import User
from .models import UserProfile

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["check_in", "check_out", "guests"]
        widgets = {
            "check_in": DateInput(attrs={"type": "date", "class": "form-control"}),
            "check_out": DateInput(attrs={"type": "date", "class": "form-control"}),
            "guests": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={"class": "form-control"}))
    
    ROLE_CHOICES = [
        ('customer', 'Guest / Customer (Book Hotels)'),
        ('manager', 'Hotel Manager / Admin (Manage Hotels & Rooms)'),
    ]
    role = forms.ChoiceField(choices=ROLE_CHOICES, initial='customer', widget=forms.RadioSelect)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

class ProfileImageForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_image']