from django.contrib import admin
from .models import *

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'contact_name', 'email', 'gst_number', 'branch_location']
    search_fields = ['company_name', 'contact_name', 'gst_number']
    list_filter = ['branch_location']

@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ['work_order_number', 'customer', 'project_title', 'total_cost', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['work_order_number', 'customer__company_name', 'project_title']
    readonly_fields = ['work_order_number', 'created_at', 'updated_at']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'total_amount', 'balance_due', 'status', 'due_date']
    list_filter = ['status', 'invoice_date']
    search_fields = ['invoice_number', 'customer__company_name']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'payment_date', 'amount', 'payment_method', 'reference_number']
    list_filter = ['payment_date', 'payment_method']
    search_fields = ['invoice__invoice_number', 'reference_number']

@admin.register(TermsAndConditions)
class TermsAndConditionsAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'is_active']
    list_filter = ['is_active']

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'subject', 'sent_at', 'status']
    list_filter = ['status', 'sent_at']
    readonly_fields = ['sent_at']

    # FD/admin.py - Add this
@admin.register(EmailConfiguration)
class EmailConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'days_after_invoice', 'reminder_frequency', 'max_reminders', 'is_active']
    list_editable = ['is_active']

@admin.register(PaymentReminderLog)
class PaymentReminderLogAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'sent_date', 'reminder_number', 'status']
    list_filter = ['sent_date', 'status']
    readonly_fields = ['sent_date']

@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'gst_number', 'is_active']
    list_editable = ['is_active']
    
    def has_add_permission(self, request):
        # Allow only one company settings record
        if CompanySettings.objects.count() >= 1:
            return False
        return True