from django.urls import path
from .views import (
    register_view, login_view, logout_view, 
    owner_dashboard, shopkeeper_dashboard,
    manage_inventory, sales_log, add_sale, 
    toggle_stock_permission, add_product, update_product, 
    delete_product, view_product, view_sales, edit_sale, 
    delete_sale, view_branches, add_branch, 
    edit_branch, delete_branch, redirect_dashboard
)

urlpatterns = [
    # Authentication
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('accounts/login/', login_view, name='login'),
    # Dashboards
    path('owner/', owner_dashboard, name='owner_dashboard'),
    path('shopkeeper/', shopkeeper_dashboard, name='shopkeeper_dashboard'),
    path('', redirect_dashboard, name='redirect_dashboard'),
    
    # Inventory Management
    path('manage-inventory/', manage_inventory, name='manage_inventory'),
    path('add-product/', add_product, name='add_product'),
    path('edit-product/<int:product_id>/', update_product, name='edit_product'),
    path('delete-product/<int:product_id>/', delete_product, name='delete_product'),
    path('view-product/<int:product_id>/', view_product, name='view_product'),
    
    # Sales Management
    path('sales-log/', sales_log, name='manage_sales'),
    path('add-sale/', add_sale, name='add_sale'),
    path('view-sales/<int:sale_id>/', view_sales, name='view_sales'),
    path('edit-sale/<int:sale_id>/', edit_sale, name='edit_sale'),
    path('delete-sale/<int:sale_id>/', delete_sale, name='delete_sale'),
    
    # Branch Management
    path('view-branches/', view_branches, name='view_branches'),
    path('add-branch/', add_branch, name='add_branch'),
    path('edit-branch/<int:branch_id>/', edit_branch, name='edit_branch'),
    path('delete-branch/<int:branch_id>/', delete_branch, name='delete_branch'),
    
    # User Permissions
    path('toggle-stock-permission/<int:user_id>/', toggle_stock_permission, name='toggle_stock_permission'),
]