# FD/views.py - COMPLETE FIXED VERSION WITH ALL IMPROVEMENTS
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import models, IntegrityError
from django.core.cache import cache
from decimal import Decimal, DecimalException
from datetime import date, timedelta, datetime
import json
import io
from .models import Customer, WorkOrder, Invoice, Payment, TermsAndConditions, EmailLog, PaymentReminderLog, EmailConfiguration, CompanySettings

# Dashboard Views with Caching
class DashboardView(View):
    def get(self, request):
        cache_key = f'dashboard_data_{request.user.id if request.user.is_authenticated else "anonymous"}'
        cached_data = cache.get(cache_key)
        
        if cached_data is None:
            cached_data = self.calculate_dashboard_data()
            cache.set(cache_key, cached_data, 300)  # Cache for 5 minutes
        
        context = cached_data
        return render(request, 'FD/dashboard.html', context)

    def calculate_dashboard_data(self):
        """Calculate dashboard data (expensive operation)"""
        # Get current financial year (April 1 to March 31)
        today = timezone.now().date()
        if today.month >= 4:
            financial_year_start = date(today.year, 4, 1)
            financial_year_end = date(today.year + 1, 3, 31)
            financial_year = f"{today.year}-{today.year + 1}"
        else:
            financial_year_start = date(today.year - 1, 4, 1)
            financial_year_end = date(today.year, 3, 31)
            financial_year = f"{today.year - 1}-{today.year}"

        # NEW DATA (Created in new system - not migrated)
        new_customers = Customer.objects.filter(is_migrated=False)
        new_work_orders = WorkOrder.objects.filter(is_migrated=False)
        new_invoices = Invoice.objects.filter(is_migrated=False)
        
        # MIGRATED DATA (Legacy data)
        migrated_customers = Customer.objects.filter(is_migrated=True)
        migrated_work_orders = WorkOrder.objects.filter(is_migrated=True)
        migrated_invoices = Invoice.objects.filter(is_migrated=True)

        # Revenue calculations for NEW data
        new_total_revenue = sum(inv.total_amount for inv in new_invoices if inv.total_amount) or 0
        new_pending_payments = sum(inv.balance_due for inv in new_invoices.exclude(status='paid') if inv.balance_due) or 0
        new_collected_revenue = new_total_revenue - new_pending_payments

        # Revenue calculations for MIGRATED data
        migrated_total_revenue = sum(inv.total_amount for inv in migrated_invoices if inv.total_amount) or 0
        migrated_pending_payments = sum(inv.balance_due for inv in migrated_invoices.exclude(status='paid') if inv.balance_due) or 0
        migrated_collected_revenue = migrated_total_revenue - migrated_pending_payments

        return {
            'financial_year': financial_year,
            
            # NEW DATA METRICS (Fresh data)
            'new_customers_count': new_customers.count(),
            'new_work_orders_count': new_work_orders.count(),
            'new_invoices_count': new_invoices.count(),
            'new_total_revenue': new_total_revenue,
            'new_pending_payments': new_pending_payments,
            'new_collected_revenue': new_collected_revenue,
            'new_collection_rate': (new_collected_revenue / new_total_revenue * 100) if new_total_revenue > 0 else 0,
            
            # MIGRATED DATA METRICS (Legacy data)
            'migrated_customers_count': migrated_customers.count(),
            'migrated_work_orders_count': migrated_work_orders.count(),
            'migrated_invoices_count': migrated_invoices.count(),
            'migrated_total_revenue': migrated_total_revenue,
            'migrated_pending_payments': migrated_pending_payments,
            'migrated_collected_revenue': migrated_collected_revenue,
            'migrated_collection_rate': (migrated_collected_revenue / migrated_total_revenue * 100) if migrated_total_revenue > 0 else 0,
            
            # Recent activities
            'recent_invoices': new_invoices.order_by('-created_at')[:5],
            'recent_work_orders': new_work_orders.order_by('-created_at')[:5],
            'overdue_invoices': new_invoices.filter(status='overdue')[:5],
        }

# Legacy Data Views
class LegacyDataView(View):
    def get(self, request):
        """Legacy data view - shows migrated data, no MySQL connection needed"""
        context = {}
        
        # Current system counts - ALL DATA (both migrated and new)
        context['current_customer_count'] = Customer.objects.count()
        context['current_workorder_count'] = WorkOrder.objects.count() 
        context['current_invoice_count'] = Invoice.objects.count()
        
        # Migrated data counts (legacy data)
        context['migrated_customer_count'] = Customer.objects.filter(is_migrated=True).count()
        context['migrated_workorder_count'] = WorkOrder.objects.filter(is_migrated=True).count()
        context['migrated_invoice_count'] = Invoice.objects.filter(is_migrated=True).count()
        context['migrated_payment_count'] = Payment.objects.filter(is_migrated=True).count()
        
        # New data counts (created in new system)
        context['new_customer_count'] = Customer.objects.filter(is_migrated=False).count()
        context['new_workorder_count'] = WorkOrder.objects.filter(is_migrated=False).count()
        context['new_invoice_count'] = Invoice.objects.filter(is_migrated=False).count()
        context['new_payment_count'] = Payment.objects.filter(is_migrated=False).count()
        
        # Recent migrated data for display
        context['recent_customers'] = Customer.objects.filter(is_migrated=True).order_by('-created_at')[:10]
        context['recent_workorders'] = WorkOrder.objects.filter(is_migrated=True).order_by('-created_at')[:10]
        context['recent_invoices'] = Invoice.objects.filter(is_migrated=True).order_by('-created_at')[:10]
        
        # Connection status - No MySQL connection needed anymore
        context['connected'] = True
        context['connection_message'] = "All legacy data has been migrated to new system"
        
        return render(request, 'FD/legacy_data.html', context)

def migrate_legacy_data_view(request):
    """Simple migration view"""
    try:
        # Check if we have customers first
        if Customer.objects.count() == 0:
            messages.error(request, 'Please create some customers first before migrating data.')
            return redirect('legacy_data')
        
        # Simple migration logic
        import pymysql
        from decimal import Decimal
        
        mysql_config = {
            'host': 'localhost',
            'user': 'root', 
            'password': 'root',
            'database': 'folkdrive'
        }
        
        try:
            connection = pymysql.connect(**mysql_config)
            
            # Migrate work orders
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM daily_orders WHERE docno IS NOT NULL")
                wo_count = cursor.fetchone()[0]
                messages.info(request, f'Found {wo_count} work orders in legacy system')
            
            connection.close()
            messages.success(request, 'Legacy database connection successful! Data can be migrated.')
            
        except Exception as e:
            messages.error(request, f'Could not connect to legacy database: {e}')
        
    except Exception as e:
        messages.error(request, f'Migration failed: {str(e)}')
    
    return redirect('legacy_data')

# Basic Views
def home_view(request):
    return render(request, 'FD/home.html')

def debug_view(request):
    context = {
        'test_data': 'This is test data from the view!',
        'customers_count': Customer.objects.count(),
        'work_orders_count': WorkOrder.objects.count(),
        'invoices_count': Invoice.objects.count(),
    }
    return render(request, 'FD/debug.html', context)

def simple_test(request):
    return HttpResponse("""
    <h1>Server is Working!</h1>
    <p>If you can see this, Django is running correctly.</p>
    <ul>
        <li><a href="/work-orders/">Work Orders</a></li>
        <li><a href="/invoices/">Invoices</a></li>
        <li><a href="/customers/">Customers</a></li>
        <li><a href="/admin/">Admin</a></li>
    </ul>
    """)

# Customer Views with Enhanced Filtering
class CustomerListView(ListView):
    model = Customer
    template_name = 'FD/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 10

    def get_queryset(self):
        queryset = Customer.objects.all().order_by('-created_at')
        
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                models.Q(company_name__icontains=search_query) |
                models.Q(contact_name__icontains=search_query) |
                models.Q(gst_number__icontains=search_query)
            )
        
        # Date range filtering
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__range=[start, end])
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get the base queryset (before pagination)
        base_queryset = self.get_queryset()
        
        # Add total counts (not paginated)
        context['total_customers_count'] = base_queryset.count()
        context['current_page_count'] = len(context['customers'])  # Current page count
        
        # Add additional context for stats
        invoices = Invoice.objects.all()
        context['total_revenue'] = sum(inv.total_amount for inv in invoices if inv.total_amount) or 0
        context['pending_payments'] = sum(inv.balance_due for inv in invoices.exclude(status='paid') if inv.balance_due) or 0
        context['active_invoices_count'] = invoices.exclude(status='paid').count()
        
        # Add filter parameters for template
        context['search_query'] = self.request.GET.get('search', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        
        return context

    def post(self, request, *args, **kwargs):
        """Handle bulk actions"""
        if 'bulk_action' in request.POST:
            selected_ids = request.POST.getlist('selected_items')
            action = request.POST.get('bulk_action')
            
            if action == 'export':
                # Handle bulk export (placeholder)
                messages.info(request, f'Export feature for {len(selected_ids)} customers coming soon!')
            elif action == 'delete':
                # Handle bulk delete
                if selected_ids:
                    customers = Customer.objects.filter(id__in=selected_ids)
                    count = customers.count()
                    customers.delete()
                    messages.success(request, f'Successfully deleted {count} customers.')
        
        return self.get(request, *args, **kwargs)
    
class CustomerCreateView(CreateView):
    model = Customer
    template_name = 'FD/customer_form.html'
    fields = ['company_name', 'contact_name', 'mobile_number', 'email', 
              'gst_number', 'address', 'branch_location']
    success_url = reverse_lazy('customer_list')

    def form_valid(self, form):
        form.instance.is_migrated = False
        messages.success(self.request, 'Customer created successfully!')
        return super().form_valid(form)

class CustomerUpdateView(UpdateView):
    model = Customer
    template_name = 'FD/customer_form.html'
    fields = ['company_name', 'contact_name', 'mobile_number', 'email', 
              'gst_number', 'address', 'branch_location']
    success_url = reverse_lazy('customer_list')

    def form_valid(self, form):
        messages.success(self.request, 'Customer updated successfully!')
        return super().form_valid(form)

class CustomerDetailView(DetailView):
    model = Customer
    template_name = 'FD/customer_detail.html'
    context_object_name = 'customer'

class CustomerDeleteView(DeleteView):
    model = Customer
    template_name = 'FD/customer_confirm_delete.html'
    success_url = reverse_lazy('customer_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Customer deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Work Order Views - UPDATED with Enhanced Features
class WorkOrderListView(ListView):
    model = WorkOrder
    template_name = 'FD/workorder_list.html'
    context_object_name = 'work_orders'
    paginate_by = 10

    def get_queryset(self):
        queryset = WorkOrder.objects.all().order_by('-created_at')
        
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                models.Q(work_order_number__icontains=search_query) |
                models.Q(customer__company_name__icontains=search_query) |
                models.Q(project_title__icontains=search_query)
            )
        
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Date range filtering
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__range=[start, end])
            except ValueError:
                pass  # Invalid date format, ignore filter
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get the base queryset (before pagination)
        base_queryset = self.get_queryset()
        
        # Add total counts (not paginated)
        context['total_work_orders_count'] = base_queryset.count()
        context['current_page_count'] = len(context['work_orders'])  # Current page count
        
        # Add filter parameters for template
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        
        return context

    def post(self, request, *args, **kwargs):
        """Handle bulk actions"""
        if 'bulk_action' in request.POST:
            selected_ids = request.POST.getlist('selected_items')
            action = request.POST.get('bulk_action')
            
            if action == 'export':
                messages.info(request, f'Export feature for {len(selected_ids)} work orders coming soon!')
            elif action == 'delete':
                if selected_ids:
                    work_orders = WorkOrder.objects.filter(id__in=selected_ids)
                    count = work_orders.count()
                    work_orders.delete()
                    messages.success(request, f'Successfully deleted {count} work orders.')
        
        return self.get(request, *args, **kwargs)

class WorkOrderCreateView(CreateView):
    model = WorkOrder
    template_name = 'FD/workorder_form.html'
    fields = ['customer', 'project_title', 'project_description', 'base_amount', 'gst_percentage', 'discount']
    success_url = reverse_lazy('workorder_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user.username if self.request.user.is_authenticated else 'System'
        form.instance.status = 'draft'
        form.instance.is_migrated = False
        
        # Get active terms and conditions from admin ONLY
        active_terms = TermsAndConditions.objects.filter(is_active=True)
        
        merged_terms = ""
        for terms in active_terms:
            merged_terms += f"{terms.content}\n\n"
        
        # Set terms - if no active terms, it will be empty
        form.instance.terms_and_conditions = merged_terms.strip()
        
        # Calculate financials
        work_order = form.save(commit=False)
        work_order.calculate_financials()
        
        response = super().form_valid(form)
        messages.success(self.request, 'Work Order created successfully!')
        return response

class WorkOrderUpdateView(UpdateView):
    model = WorkOrder
    template_name = 'FD/workorder_form.html'
    fields = ['customer', 'project_title', 'project_description', 'base_amount', 'gst_percentage', 'discount', 'status']
    success_url = reverse_lazy('workorder_list')

    def form_valid(self, form):
        # Calculate financials before saving
        work_order = form.save(commit=False)
        work_order.calculate_financials()
        
        messages.success(self.request, 'Work Order updated successfully!')
        return super().form_valid(form)
    
class WorkOrderDetailView(DetailView):
    model = WorkOrder
    template_name = 'FD/workorder_detail.html'
    context_object_name = 'work_order'

class WorkOrderDeleteView(DeleteView):
    model = WorkOrder
    template_name = 'FD/workorder_confirm_delete.html'
    success_url = reverse_lazy('workorder_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Work Order deleted successfully!')
        return super().delete(request, *args, **kwargs)

class ConvertToInvoiceView(View):
    def get(self, request, pk):
        """Show elegant conversion form with payment options"""
        work_order = get_object_or_404(WorkOrder, pk=pk)
        
        if work_order.status not in ['confirmed', 'completed']:
            messages.error(request, 'Only confirmed or completed work orders can be converted to invoices.')
            return redirect('workorder_detail', pk=pk)
        
        if hasattr(work_order, 'invoice'):
            messages.warning(request, 'Invoice already exists for this Work Order.')
            return redirect('workorder_detail', pk=pk)
        
        context = {
            'work_order': work_order,
            'today': timezone.now().date().isoformat(),  # Convert to string for HTML input
            'due_date': (timezone.now().date() + timedelta(days=30)).isoformat(),  # Convert to string
        }
        return render(request, 'FD/convert_to_invoice.html', context)

    def post(self, request, pk):
        """Handle invoice creation with optional payment"""
        work_order = get_object_or_404(WorkOrder, pk=pk)
        
        try:
            # Get form data
            invoice_date_str = request.POST.get('invoice_date')
            due_date_str = request.POST.get('due_date')
            payment_amount = Decimal(request.POST.get('payment_amount', '0.00') or '0.00')
            payment_method = request.POST.get('payment_method', '')
            reference_number = request.POST.get('reference_number', '')
            payment_notes = request.POST.get('payment_notes', '')
            
            # GST fields
            hsn_code = request.POST.get('hsn_code', '998314')
            sac_code = request.POST.get('sac_code', '998314')
            place_of_supply = request.POST.get('place_of_supply', 'Gujarat')
            
            # Convert string dates to date objects
            invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            
            # Calculate amounts from work order
            base_amount = work_order.base_amount
            gst_percentage = work_order.gst_percentage
            gst_amount = work_order.gst_amount
            subtotal = base_amount - work_order.discount_amount
            total_amount = work_order.total_cost
            
            # Create invoice with CORRECT fields
            invoice = Invoice(
                work_order=work_order,
                customer=work_order.customer,
                invoice_date=invoice_date,  # Now date object
                due_date=due_date,  # Now date object
                base_amount=base_amount,
                gst_percentage=gst_percentage,
                gst_amount=gst_amount,
                subtotal=subtotal,
                total_amount=total_amount,
                amount_paid=Decimal('0.00'),
                balance_due=total_amount,
                terms_and_conditions=work_order.terms_and_conditions,
                status='sent',
                is_migrated=False,
                # GST fields
                hsn_code=hsn_code,
                sac_code=sac_code,
                place_of_supply=place_of_supply,
                is_service=True,
                payment_collected_at_conversion=bool(payment_amount > 0)
            )
            
            # Calculate GST breakup and save
            invoice.calculate_gst_breakup()
            invoice.save()
            
            # Handle payment if provided
            if payment_amount > 0:
                payment = Payment.objects.create(
                    invoice=invoice,
                    payment_date=timezone.now().date(),
                    amount=payment_amount,
                    payment_method=payment_method,
                    reference_number=reference_number,
                    notes=payment_notes,
                    is_migrated=False
                )
                
                # Update invoice payment status through the payment save method
                # This will trigger the invoice status update
                
            # Redirect to invoice preview instead of detail
            messages.success(request, f'Invoice {invoice.invoice_number} created successfully!')
            return redirect('invoice_preview', pk=invoice.pk)
            
        except Exception as e:
            messages.error(request, f'Error creating invoice: {str(e)}')
            import traceback
            print(traceback.format_exc())  # For debugging
            return redirect('workorder_detail', pk=pk)

class InvoicePreviewView(DetailView):
    """Show invoice preview with payment details before printing"""
    model = Invoice
    template_name = 'FD/invoice_preview.html'
    context_object_name = 'invoice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get payment details
        context['payments'] = self.object.payments.all()
        context['total_paid'] = self.object.amount_paid
        context['balance_due'] = self.object.balance_due
        
        # Get company settings for GST details
        try:
            context['company_settings'] = CompanySettings.objects.filter(is_active=True).first()
        except:
            context['company_settings'] = None
            
        return context
          
class PrintWorkOrderView(DetailView):
    model = WorkOrder
    template_name = 'FD/print_workorder.html'
    context_object_name = 'work_order'

# Invoice Views with Enhanced Features
class InvoiceListView(ListView):
    model = Invoice
    template_name = 'FD/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 10

    def get_queryset(self):
        queryset = Invoice.objects.all().order_by('-created_at')
        
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                models.Q(invoice_number__icontains=search_query) |
                models.Q(customer__company_name__icontains=search_query) |
                models.Q(work_order__project_title__icontains=search_query)
            )
        
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Date range filtering
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__range=[start, end])
            except ValueError:
                pass  # Invalid date format, ignore filter
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get the base queryset (before pagination)
        base_queryset = self.get_queryset()
        
        # Add total counts (not paginated)
        context['total_invoices_count'] = base_queryset.count()
        context['current_page_count'] = len(context['invoices'])  # Current page count
        
        invoices = Invoice.objects.all()
        total_revenue = sum(inv.total_amount for inv in invoices if inv.total_amount) or 0
        pending_payments = sum(inv.balance_due for inv in invoices.exclude(status='paid') if inv.balance_due) or 0
        collected_revenue = total_revenue - pending_payments
        
        context['total_revenue'] = total_revenue
        context['pending_payments'] = pending_payments
        context['collection_rate'] = (collected_revenue / total_revenue * 100) if total_revenue > 0 else 0
        
        # Add filter parameters for template
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        
        return context

    def post(self, request, *args, **kwargs):
        """Handle bulk actions"""
        if 'bulk_action' in request.POST:
            selected_ids = request.POST.getlist('selected_items')
            action = request.POST.get('bulk_action')
            
            if action == 'export':
                messages.info(request, f'Export feature for {len(selected_ids)} invoices coming soon!')
            elif action == 'delete':
                if selected_ids:
                    invoices = Invoice.objects.filter(id__in=selected_ids)
                    count = invoices.count()
                    invoices.delete()
                    messages.success(request, f'Successfully deleted {count} invoices.')
        
        return self.get(request, *args, **kwargs)
    
class InvoiceDetailView(DetailView):
    model = Invoice
    template_name = 'FD/invoice_detail.html'
    context_object_name = 'invoice'

class InvoiceUpdateView(UpdateView):
    model = Invoice
    template_name = 'FD/invoice_form.html'
    fields = ['due_date', 'status', 'terms_and_conditions']
    success_url = reverse_lazy('invoice_list')

    def form_valid(self, form):
        messages.success(self.request, 'Invoice updated successfully!')
        return super().form_valid(form)

class InvoiceDeleteView(DeleteView):
    model = Invoice
    template_name = 'FD/invoice_confirm_delete.html'
    success_url = reverse_lazy('invoice_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Invoice deleted successfully!')
        return super().delete(request, *args, **kwargs)

class PrintInvoiceView(DetailView):
    model = Invoice
    template_name = 'FD/print_invoice_enhanced.html'
    context_object_name = 'invoice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get active company settings
        try:
            context['company_settings'] = CompanySettings.objects.filter(is_active=True).first()
        except Exception as e:
            print(f"Error fetching company settings: {e}")
            context['company_settings'] = None
        return context

# PDF Export Functionality with Error Handling
def export_invoice_pdf(request, pk):
    """Export invoice as PDF with fallback to HTML if reportlab not available"""
    try:
        # Try to import reportlab
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.units import inch
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        
        invoice = get_object_or_404(Invoice, pk=pk)
        company_settings = CompanySettings.objects.filter(is_active=True).first()
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
        styles = getSampleStyleSheet()
        story = []
        
        # Add company header
        if company_settings:
            story.append(Paragraph(company_settings.company_name, styles['Title']))
            story.append(Paragraph(company_settings.address, styles['Normal']))
            story.append(Paragraph(f"GST: {company_settings.gst_number}", styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Add invoice header
        story.append(Paragraph(f"INVOICE: {invoice.invoice_number}", styles['Heading1']))
        story.append(Spacer(1, 0.2*inch))
        
        # Add invoice details
        story.append(Paragraph(f"Date: {invoice.invoice_date}", styles['Normal']))
        story.append(Paragraph(f"Due Date: {invoice.due_date}", styles['Normal']))
        story.append(Paragraph(f"Customer: {invoice.customer.company_name}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Add amount details
        data = [
            ['Description', 'Amount'],
            ['Base Amount', f"₹{invoice.base_amount}"],
            ['GST ({invoice.gst_percentage}%)', f"₹{invoice.gst_amount}"],
            ['Total Amount', f"₹{invoice.total_amount}"],
            ['Amount Paid', f"₹{invoice.amount_paid}"],
            ['Balance Due', f"₹{invoice.balance_due}"],
        ]
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.2*inch))
        
        # Add terms and conditions
        if invoice.terms_and_conditions:
            story.append(Paragraph("Terms & Conditions:", styles['Heading2']))
            story.append(Paragraph(invoice.terms_and_conditions, styles['Normal']))
        
        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response
        
    except ImportError:
        # Fallback: redirect to print view with message
        messages.warning(request, 'PDF export requires reportlab library. Please install it: pip install reportlab')
        return redirect('print_invoice', pk=pk)
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('invoice_detail', pk=pk)
    
# Payment Views
class PaymentCreateView(CreateView):
    model = Payment
    template_name = 'FD/payment_form.html'
    fields = ['payment_date', 'amount', 'payment_method', 'reference_number', 'notes']
    
    def dispatch(self, request, *args, **kwargs):
        self.invoice = get_object_or_404(Invoice, pk=kwargs.get('invoice_id'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_initial(self):
        initial = super().get_initial()
        initial['amount'] = self.invoice.balance_due
        initial['payment_date'] = timezone.now().date()
        return initial
    
    def form_valid(self, form):
        form.instance.invoice = self.invoice
        form.instance.is_migrated = False
        response = super().form_valid(form)
        messages.success(self.request, 'Payment recorded successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('invoice_detail', kwargs={'pk': self.invoice.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invoice'] = self.invoice
        return context

class PaymentDeleteView(DeleteView):
    model = Payment
    template_name = 'FD/payment_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('invoice_detail', kwargs={'pk': self.object.invoice.pk})
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Payment deleted successfully!')
        return super().delete(request, *args, **kwargs)

# API Views
class GSTLookupView(View):
    def get(self, request):
        gst_number = request.GET.get('gst_number', '').strip()
        
        if not gst_number:
            return JsonResponse({'success': False, 'error': 'GST number is required'})
        
        existing_customer = Customer.objects.filter(gst_number=gst_number).first()
        if existing_customer:
            return JsonResponse({
                'success': True,
                'company_name': existing_customer.company_name,
                'address': existing_customer.address,
                'contact_name': existing_customer.contact_name,
                'email': existing_customer.email,
                'mobile_number': existing_customer.mobile_number,
                'from_database': True
            })
        
        company_data = self.fetch_gst_details(gst_number)
        return JsonResponse(company_data)
    
    def fetch_gst_details(self, gst_number):
        try:
            if len(gst_number) != 15:
                return {'success': False, 'error': 'Invalid GST number format'}
                
            return {
                'company_name': f'Company for GST {gst_number}',
                'address': '123 Business Street, City, State - 560001',
                'contact_name': 'Business Owner',
                'email': f'contact{gst_number}@company.com',
                'mobile_number': '9876543210',
                'success': True,
                'from_api': True
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

class ProjectAnalyticsView(View):
    def get(self, request, project_id):
        try:
            work_order = get_object_or_404(WorkOrder, pk=project_id)
            analytics_data = self.calculate_project_analytics(work_order)
            
            return JsonResponse({
                'success': True,
                'project': work_order.project_title,
                'analytics': analytics_data
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    def calculate_project_analytics(self, work_order):
        similar_projects = WorkOrder.objects.filter(
            status='completed'
        )
        
        actual_cost = float(work_order.total_cost) if work_order.total_cost else 0
        
        if similar_projects.exists():
            avg_cost = sum(float(proj.total_cost) for proj in similar_projects if proj.total_cost) / len(similar_projects)
            cost_variance = ((actual_cost - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0
        else:
            avg_cost = actual_cost
            cost_variance = 0
        
        return {
            'cost_variance_percentage': round(cost_variance, 1),
            'budget_health': 'within_budget' if cost_variance <= 10 else 'over_budget',
            'similar_projects_comparison': len(similar_projects)
        }

# AI Analytics View
class AIAnalyticsView(View):
    def get(self, request):
        # Get real data for predictions
        from django.utils import timezone
        from datetime import timedelta
        from decimal import Decimal
        
        # Current data analysis
        total_customers = Customer.objects.count()
        total_invoices = Invoice.objects.count()
        total_revenue = sum(inv.total_amount for inv in Invoice.objects.all() if inv.total_amount) or Decimal('0')
        
        # Calculate growth rates from last 3 months
        three_months_ago = timezone.now() - timedelta(days=90)
        
        # Customer growth calculation
        recent_customers = Customer.objects.filter(created_at__gte=three_months_ago).count()
        customer_growth_rate = (recent_customers / total_customers * 100) if total_customers > 0 else 0
        
        # Revenue growth calculation
        recent_revenue = sum(
            inv.total_amount for inv in 
            Invoice.objects.filter(created_at__gte=three_months_ago) 
            if inv.total_amount
        ) or Decimal('0')
        revenue_growth_rate = (recent_revenue / total_revenue * 100) if total_revenue > 0 else 0
        
        # AI Predictions based on real data
        predicted_customers = int(total_customers * (1 + customer_growth_rate/100))
        predicted_revenue = total_revenue * (1 + revenue_growth_rate/100)
        
        # Payment analysis
        paid_invoices = Invoice.objects.filter(status='paid')
        pending_invoices = Invoice.objects.filter(status__in=['sent', 'partially_paid'])
        overdue_invoices = Invoice.objects.filter(status='overdue')
        
        context = {
            # Real current data
            'total_customers': total_customers,
            'total_invoices': total_invoices,
            'total_revenue': total_revenue,
            
            # AI Predictions
            'predicted_customers': predicted_customers,
            'predicted_revenue': predicted_revenue,
            'customer_growth_rate': round(customer_growth_rate, 1),
            'revenue_growth_rate': round(revenue_growth_rate, 1),
            
            # Payment analysis
            'paid_invoices_count': paid_invoices.count(),
            'pending_invoices_count': pending_invoices.count(),
            'overdue_invoices_count': overdue_invoices.count(),
            'paid_amount': sum(inv.total_amount for inv in paid_invoices if inv.total_amount) or Decimal('0'),
            'pending_amount': sum(inv.balance_due for inv in pending_invoices if inv.balance_due) or Decimal('0'),
            
            # Financial year
            'financial_year': self.get_financial_year(),
        }
        return render(request, 'FD/ai_analytics.html', context)
    
    def get_financial_year(self):
        from datetime import datetime
        today = datetime.now()
        if today.month >= 4:
            return f"{today.year}-{today.year + 1}"
        else:
            return f"{today.year - 1}-{today.year}"

# Email & Automation Views
class AutomatedEmailView(View):
    def get(self, request):
        # Get email configuration
        email_config = EmailConfiguration.objects.filter(is_active=True).first()
        
        # Get only NEW invoices (not migrated) that need reminders
        overdue_invoices = Invoice.objects.filter(
            is_migrated=False,  # Only new system invoices
            status__in=['sent', 'overdue'],
            balance_due__gt=0
        )
        
        # Calculate scheduled emails
        scheduled_emails = self.get_scheduled_emails()
        
        context = {
            'overdue_invoices': overdue_invoices,
            'email_config': email_config,
            'scheduled_emails': scheduled_emails,
            'sent_emails_count': EmailLog.objects.count(),
        }
        return render(request, 'FD/send_reminders.html', context)
    
    def get_scheduled_emails(self):
        """Get scheduled emails based on configuration"""
        email_config = EmailConfiguration.objects.filter(is_active=True).first()
        if not email_config:
            return []
        
        # This is a simplified version - implement your actual scheduling logic
        scheduled = []
        invoices = Invoice.objects.filter(
            status__in=['sent', 'overdue'],
            balance_due__gt=0
        )
        
        for invoice in invoices:
            scheduled.append({
                'invoice': invoice,
                'scheduled_date': timezone.now() + timedelta(days=email_config.days_after_invoice),
                'reminder_number': 1
            })
        
        return scheduled