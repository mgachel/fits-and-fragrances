from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings


class User(AbstractUser):
    is_shopkeeper = models.BooleanField(default=False)
    is_owner = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='core_user_set',
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='core_user_set',
        blank=True,
    )

    def __str__(self):
        return self.username


class Branch(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=50)
    stock = models.PositiveIntegerField(default=0)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.stock}"


class Sale(models.Model):
    MODES_OF_PAYMENT = [
        ('cash', 'Cash'),
        ('momo', 'Momo'),
        ('bank transfer', 'Bank Transfer'),
    ]
    
    customer_name = models.CharField(max_length=50, null=True, blank=True)
    customer_contact_details = models.CharField(max_length=50, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_sold = models.PositiveIntegerField()
    amount_paid = models.DecimalField(decimal_places=2, max_digits=10)
    amount_left = models.DecimalField(decimal_places=2, max_digits=10)
    mode = models.CharField(max_length=20, choices=MODES_OF_PAYMENT)
    shopkeeper = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    
    
    @property
    def profit(self):
        # Example calculation: profit = amount_paid - cost (assuming cost is available)
        cost = self.product.cost_price * self.quantity_sold
        return self.amount_paid - cost
    
    
    def total_price(self):
        return self.quantity_sold * self.product.selling_price


class ShopkeeperPermission(models.Model):
    shopkeeper = models.OneToOneField(User, on_delete=models.CASCADE)
    can_edit_stock = models.BooleanField(default=False)