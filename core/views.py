from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm, UserRegistrationForm, SaleForm, ProductForm, BranchForm
from django.contrib.auth.decorators import login_required
from .models import User, Product, Sale, ShopkeeperPermission, Branch
from datetime import timedelta, datetime
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, F, FloatField, Count, Avg, ExpressionWrapper, DecimalField
import pdfkit
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.models import Group
from django.contrib import messages
from django.db.models.functions import TruncMonth
from django.utils.timezone import now
from datetime import date, timedelta

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Set is_shopkeeper to True by default for new registrations if needed
            user.is_shopkeeper = True
            user.save()
            
            # Make sure the group exists first
            shopkeeper_group, created = Group.objects.get_or_create(name='Shopkeeper')
            user.groups.add(shopkeeper_group)
            
            # Create permissions
            ShopkeeperPermission.objects.create(shopkeeper=user, can_edit_stock=False)
            
            messages.success(request, 'Account created successfully! You can now log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Redirect based on user group
                if user.is_staff or user.is_superuser or user.groups.filter(name='Owner').exists():
                    return redirect('owner_dashboard')
                elif user.groups.filter(name='Manager').exists():
                    return redirect('manager_dashboard')
                elif user.groups.filter(name='Shopkeeper').exists():
                    return redirect('shopkeeper_dashboard')
                else:
                    return redirect('default_dashboard')
            else:
                messages.error(request, 'Invalid username or password')
                return render(request, 'login.html', {'form': form, 'error': 'Invalid username or password'})
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully')
    return redirect('login')


@login_required
def redirect_dashboard(request):
    user = request.user
    if user.is_staff or user.is_superuser or user.groups.filter(name="Owner").exists():
        return redirect("owner_dashboard")
    elif user.groups.filter(name="Manager").exists():
        return redirect("manager_dashboard")
    elif user.groups.filter(name="Shopkeeper").exists():
        return redirect("shopkeeper_dashboard")
    else:
        return redirect("login")


@login_required
def shopkeeper_dashboard(request):
    if not (request.user.groups.filter(name='Shopkeeper').exists() or request.user.is_staff or request.user.is_superuser):
        return redirect('redirect_dashboard')

    sales_today = Sale.objects.filter(
        shopkeeper=request.user,
        timestamp__date=timezone.now().date()
    ).order_by('-timestamp')

    sales_week = Sale.objects.filter(
        shopkeeper=request.user,
        timestamp__gte=timezone.now() - timedelta(days=7)
    ).order_by('-timestamp')

    inventory = Product.objects.all().order_by('name')
    permission = ShopkeeperPermission.objects.filter(shopkeeper=request.user).first()
    can_edit_stock = permission.can_edit_stock if permission else False

    return render(request, 'shopkeeper_dashboard.html', {
        'sales_today': sales_today,
        'sales_week': sales_week,
        'inventory': inventory,
        'can_edit_stock': can_edit_stock,
    })


@staff_member_required
def owner_dashboard(request):
    # Calculate total revenue
    total_revenue = Sale.objects.aggregate(total=Sum('amount_paid'))['total'] or 0
    today = date.today()
    first_day_of_month = today.replace(day=1)
    
    
    # Calculate profit dynamically
    profit = Sale.objects.annotate(
        profit=ExpressionWrapper(
            (F('product__selling_price') - F('product__cost_price')) * F('quantity_sold'),
            output_field=DecimalField()
        )
    ).aggregate(total_profit=Sum('profit'))['total_profit'] or 0
    daily_sales = Sale.objects.filter(timestamp__date=today).annotate(
        profit=ExpressionWrapper(
            (F('product__selling_price') - F('product__cost_price')) * F('quantity_sold'),
            output_field=DecimalField()
        )
    )
    daily_profit = daily_sales.aggregate(total_profit=Sum('profit'))['total_profit'] or 0
    
    monthly_sales = Sale.objects.filter(timestamp__date__gte=first_day_of_month).annotate(
        profit=ExpressionWrapper(
            (F('product__selling_price') - F('product__cost_price')) * F('quantity_sold'),
            output_field=DecimalField()
        )
    )
    monthly_profit = monthly_sales.aggregate(total_profit=Sum('profit'))['total_profit'] or 0

    # Other calculations
    monthly_revenue = Sale.objects.filter(timestamp__month=now().month).aggregate(total=Sum('amount_paid'))['total'] or 0
    weekly_revenue = Sale.objects.filter(timestamp__week=now().isocalendar()[1]).aggregate(total=Sum('amount_paid'))['total'] or 0
    total_sales_count = Sale.objects.count()
    total_products_count = Product.objects.count()
    active_shopkeepers_count = User.objects.filter(groups__name='Shopkeeper', is_active=True).count()
    total_shopkeepers_count = User.objects.filter(groups__name='Shopkeeper').count()
    average_sale_value = Sale.objects.aggregate(avg=Sum('amount_paid') / Sum('quantity_sold'))['avg'] or 0
    recent_sales = Sale.objects.order_by('-timestamp')[:10]
    shopkeepers = User.objects.filter(groups__name='Shopkeeper')

    context = {
        'total_revenue': total_revenue,
        'profit': profit,
        'monthly_revenue': monthly_revenue,
        'weekly_revenue': weekly_revenue,
        'total_sales_count': total_sales_count,
        'total_products_count': total_products_count,
        'active_shopkeepers_count': active_shopkeepers_count,
        'total_shopkeepers_count': total_shopkeepers_count,
        'average_sale_value': average_sale_value,
        'recent_sales': recent_sales,
        'daily_profit': daily_profit,
        'monthly_profit': monthly_profit,
        'shopkeepers': shopkeepers,
    }
    return render(request, 'owner_dashboard.html', context)

@login_required
def add_sale(request):

    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.shopkeeper = request.user
            product = sale.product
            
            if product.stock < sale.quantity_sold:
                return render(request, 'add_sale.html', {'form': form, 'error': 'Insufficient stock for this product.'})

            sale.branch = product.branch
            sale.save()
            product.stock -= sale.quantity_sold
            product.save()
            return redirect('manage_sales')
    else:
        form = SaleForm()

    return render(request, 'add_sale.html', {'form': form})


@login_required
def sales_log(request):
    filter_date_str = request.GET.get('date', None)
    customer_name_filter = request.GET.get('customer_name', None)
    shopkeeper_filter = request.GET.get('shopkeeper', None)
    branch_filter = request.GET.get('branch', None)

    if filter_date_str:
        try:
            filter_date = datetime.strptime(filter_date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = datetime.today().date()
    else:
        filter_date = datetime.today().date()

    sales = Sale.objects.all().select_related('product', 'shopkeeper', 'branch').order_by('-timestamp')
    sales = sales.filter(timestamp__date=filter_date)

    if customer_name_filter:
        sales = sales.filter(customer_name__icontains=customer_name_filter)

    if shopkeeper_filter:
        sales = sales.filter(shopkeeper__username__icontains=shopkeeper_filter)

    if branch_filter:
        sales = sales.filter(branch__name__icontains=branch_filter)
        
    today = now().date()
    current_month = now().month
    current_year = now().year

    # Calculate daily revenue and profit
    daily_sales = Sale.objects.filter(timestamp__date=today).annotate(
        profit=ExpressionWrapper(
            F('amount_paid') - (F('product__cost_price') * F('quantity_sold')),
            output_field=DecimalField()
        )
    )
    daily_revenue = daily_sales.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    daily_profit = daily_sales.aggregate(Sum('profit'))['profit__sum'] or 0

    # Calculate monthly revenue and profit
    monthly_sales = Sale.objects.filter(timestamp__month=current_month, timestamp__year=current_year).annotate(
        profit=ExpressionWrapper(
            F('amount_paid') - (F('product__cost_price') * F('quantity_sold')),
            output_field=DecimalField()
        )
    )
    monthly_revenue = monthly_sales.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    monthly_profit = monthly_sales.aggregate(Sum('profit'))['profit__sum'] or 0

    # Calculate total revenue
    total_revenue = Sale.objects.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0

    shopkeepers = User.objects.filter(groups__name='Shopkeeper').order_by('username')
    branches = Branch.objects.all().order_by('name')

    # Determine if the user is an owner
    is_owner = request.user.groups.filter(name="Owner").exists() or request.user.is_superuser

    return render(request, 'sales_log.html', {
        'sales': sales,
        'filter_date': filter_date,
        'customer_name_filter': customer_name_filter,
        'shopkeeper_filter': shopkeeper_filter,
        'branch_filter': branch_filter,
        'shopkeepers': shopkeepers,
        'branches': branches,
        'daily_revenue': daily_revenue,
        'daily_profit': daily_profit,
        'monthly_revenue': monthly_revenue,
        'monthly_profit': monthly_profit,
        'total_revenue': total_revenue,
        'is_owner': is_owner,
    })


@staff_member_required
def view_sales(request, sale_id):
    sale = get_object_or_404(Sale.objects.select_related('product', 'shopkeeper', 'branch'), pk=sale_id)
    return render(request, 'view_sale.html', {'sale': sale})


@staff_member_required
def edit_sale(request, sale_id):
    sale = get_object_or_404(Sale.objects.select_related('product'), pk=sale_id)

    if request.method == 'POST':
        form = SaleForm(request.POST, instance=sale)
        if form.is_valid():
            old_quantity = sale.quantity_sold
            new_quantity = form.cleaned_data['quantity_sold']
            stock_change = old_quantity - new_quantity

            sale = form.save(commit=False)
            product = sale.product
            product.stock += stock_change
            product.save()
            sale.save()
            return redirect('manage_sales')
    else:
        form = SaleForm(instance=sale)

    return render(request, 'edit_sale.html', {'form': form, 'sale': sale})


@staff_member_required
def delete_sale(request, sale_id):
    sale = get_object_or_404(Sale.objects.select_related('product'), pk=sale_id)
    product = sale.product
    product.stock += sale.quantity_sold
    product.save()
    sale.delete()
    return redirect('manage_sales')


@login_required
def manage_inventory(request):
    items = Product.objects.all().select_related('branch').order_by('name')
    return render(request, 'manage_inventory.html', {'items': items})


@staff_member_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('manage_inventory')
    else:
        form = ProductForm()

    return render(request, 'add_product.html', {'form': form})


@staff_member_required
def update_product(request, product_id):
    product = get_object_or_404(Product.objects.select_related('branch'), pk=product_id)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('manage_inventory')
    else:
        form = ProductForm(instance=product)

    return render(request, 'update_product.html', {'form': form, 'product': product})


@staff_member_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    product.delete()
    return redirect('manage_inventory')


@staff_member_required
def view_product(request, product_id):
    product = get_object_or_404(Product.objects.select_related('branch'), pk=product_id)
    return render(request, 'view_product.html', {'product': product})


@staff_member_required
def low_stock_items(request):
    low_stock_items = Product.objects.filter(
        low_stock_threshold__isnull=False, 
        stock__lt=F('low_stock_threshold')
    ).select_related('branch').order_by('name')
    return render(request, 'low_stock_items.html', {'low_stock_items': low_stock_items})


@staff_member_required
def manage_shopkeepers(request):
    shopkeepers = User.objects.filter(groups__name='Shopkeeper').order_by('username')
    for shopkeeper in shopkeepers:
        shopkeeper.permission = ShopkeeperPermission.objects.filter(shopkeeper=shopkeeper).first()
    return render(request, 'manage_shopkeepers.html', {'shopkeepers': shopkeepers})


@staff_member_required
def view_shopkeeper(request, user_id):
    shopkeeper = get_object_or_404(User.objects.filter(groups__name='Shopkeeper'), pk=user_id)
    permission = ShopkeeperPermission.objects.filter(shopkeeper=shopkeeper).first()
    shopkeeper_sales = Sale.objects.filter(shopkeeper=shopkeeper).order_by('-timestamp')[:20]
    return render(request, 'view_shopkeeper.html', {
        'shopkeeper': shopkeeper,
        'permission': permission,
        'shopkeeper_sales': shopkeeper_sales,
    })


@staff_member_required
def edit_shopkeeper(request, user_id):
    shopkeeper = get_object_or_404(User.objects.filter(groups__name='Shopkeeper'), pk=user_id)

    from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm

    class ShopkeeperEditForm(BaseUserChangeForm):
        class Meta(BaseUserChangeForm.Meta):
            model = User
            fields = ('username', 'email', 'is_active', 'first_name', 'last_name')

    if request.method == 'POST':
        form = ShopkeeperEditForm(request.POST, instance=shopkeeper)
        if form.is_valid():
            form.save()
            return redirect('manage_shopkeepers')
    else:
        form = ShopkeeperEditForm(instance=shopkeeper)

    permission, created = ShopkeeperPermission.objects.get_or_create(shopkeeper=shopkeeper)

    return render(request, 'edit_shopkeeper.html', {
        'form': form,
        'shopkeeper': shopkeeper,
        'permission': permission
    })


@staff_member_required
def toggle_stock_permission(request, user_id):
    shopkeeper = get_object_or_404(User.objects.filter(groups__name='Shopkeeper'), pk=user_id)
    permission, created = ShopkeeperPermission.objects.get_or_create(shopkeeper=shopkeeper)
    permission.can_edit_stock = not permission.can_edit_stock
    permission.save()
    return redirect('view_shopkeeper', user_id=user_id)


@staff_member_required
def activate_shopkeeper(request, user_id):
    shopkeeper = get_object_or_404(User.objects.filter(groups__name='Shopkeeper'), pk=user_id)
    shopkeeper.is_active = True
    shopkeeper.save()
    return redirect('manage_shopkeepers')


@staff_member_required
def deactivate_shopkeeper(request, user_id):
    shopkeeper = get_object_or_404(User.objects.filter(groups__name='Shopkeeper'), pk=user_id)
    if request.user.id != shopkeeper.id:
        shopkeeper.is_active = False
        shopkeeper.save()
    return redirect('manage_shopkeepers')


@staff_member_required
def view_branches(request):
    branches = Branch.objects.all().order_by('name')
    return render(request, 'view_branches.html', {'branches': branches})


@staff_member_required
def add_branch(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('view_branches')
    else:
        form = BranchForm()

    return render(request, 'add_branch.html', {'form': form})


@staff_member_required
def edit_branch(request, branch_id):
    branch = get_object_or_404(Branch, pk=branch_id)

    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            return redirect('view_branches')
    else:
        form = BranchForm(instance=branch)

    return render(request, 'edit_branch.html', {'form': form, 'branch': branch})


@staff_member_required
def delete_branch(request, branch_id):
    branch = get_object_or_404(Branch, pk=branch_id)
    branch.delete()
    return redirect('view_branches')


@staff_member_required
def view_branch(request, branch_id):
    branch = get_object_or_404(Branch, pk=branch_id)
    products_in_branch = Product.objects.filter(branch=branch).order_by('name')
    sales_at_branch = Sale.objects.filter(branch=branch).order_by('-timestamp')[:20]

    return render(request, 'view_branch.html', {
        'branch': branch,
        'products_in_branch': products_in_branch,
        'sales_at_branch': sales_at_branch,
    })


@staff_member_required
def reports_view(request):
    return render(request, 'reports.html')


@staff_member_required
def settings_view(request):
    return render(request, 'settings.html')


@staff_member_required
def download_sales_report(request):
    sales = Sale.objects.select_related('product', 'shopkeeper').order_by('-timestamp')[:100]
    html = render_to_string('sales_pdf.html', {'sales': sales})

    try:
        pdf = pdfkit.from_string(html, False)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'
        return response
    except OSError as e:
        return HttpResponse(f"Error generating PDF: {e}. Make sure wkhtmltopdf is installed and in your system's PATH.", status=500)



