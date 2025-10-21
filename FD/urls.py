# FD/urls.py - UPDATED VERSION WITH PDF EXPORT
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard and Home
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('home/', views.home_view, name='home'),
    path('debug/', views.debug_view, name='debug'),
    path('test/', views.simple_test, name='test'),
    
    # Customers
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_edit'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    
    # Work Orders
    path('work-orders/', views.WorkOrderListView.as_view(), name='workorder_list'),
    path('work-orders/create/', views.WorkOrderCreateView.as_view(), name='workorder_create'),
    path('work-orders/<int:pk>/', views.WorkOrderDetailView.as_view(), name='workorder_detail'),
    path('work-orders/<int:pk>/edit/', views.WorkOrderUpdateView.as_view(), name='workorder_edit'),
    path('work-orders/<int:pk>/delete/', views.WorkOrderDeleteView.as_view(), name='workorder_delete'),
    path('work-orders/<int:pk>/convert-to-invoice/', views.ConvertToInvoiceView.as_view(), name='convert_to_invoice'),
    path('work-orders/<int:pk>/print/', views.PrintWorkOrderView.as_view(), name='print_workorder'),
    
    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.InvoiceUpdateView.as_view(), name='invoice_edit'),
    path('invoices/<int:pk>/delete/', views.InvoiceDeleteView.as_view(), name='invoice_delete'),
    path('invoices/<int:pk>/print/', views.PrintInvoiceView.as_view(), name='print_invoice'),
    path('invoices/<int:pk>/preview/', views.InvoicePreviewView.as_view(), name='invoice_preview'),
    path('invoices/<int:pk>/export-pdf/', views.export_invoice_pdf, name='export_invoice_pdf'),
    
    # Payments
    path('invoices/<int:invoice_id>/add-payment/', views.PaymentCreateView.as_view(), name='add_payment'),
    path('payments/<int:pk>/delete/', views.PaymentDeleteView.as_view(), name='payment_delete'),
    
    # Legacy Data
    path('legacy-data/', views.LegacyDataView.as_view(), name='legacy_data'),
    path('migrate-legacy/', views.migrate_legacy_data_view, name='migrate_legacy_data'),
    
    # Automation & API
    path('send-reminders/', views.AutomatedEmailView.as_view(), name='send_reminders'),
    path('api/gst-lookup/', views.GSTLookupView.as_view(), name='gst_lookup'),
    path('api/project-analytics/<int:project_id>/', views.ProjectAnalyticsView.as_view(), name='project_analytics'),
    
    # AI Analytics Dashboard
    path('ai-analytics/', views.AIAnalyticsView.as_view(), name='ai_dashboard'),
]