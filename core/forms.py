from django import forms 
from .models import User,Product, Sale, Branch
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        required=True
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        required=True
    )
    
    
class SaleForm( forms.ModelForm):
    class Meta:
        model = Sale 
        fields = ['customer_name','customer_contact_details','product', 'quantity_sold', 'amount_paid','amount_left', 'mode']
    

class ProductForm(forms.ModelForm):
    class Meta:
        model =  Product 
        fields = ['name','cost_price','selling_price','stock','low_stock_threshold','branch']
        

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['name', 'location']
        

