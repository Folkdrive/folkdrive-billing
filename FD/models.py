# FD/models.py - COMPLETE ENHANCED VERSION WITH VALIDATIONS
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal, DecimalException
from django.utils import timezone
from datetime import date
import random
import string
import re

def validate_gst_number(value):
    """Validate GST number format"""
    if not value:
        return
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    if not re.match(pattern, value):
        raise ValidationError('Invalid GST number format. Expected: 00AAAAA0000A0Z0')

def validate_mobile_number(value):
    """Validate Indian mobile number format"""
    if not value:
        return
    pattern = r'^[6-9]\d{9}$'
    if not re.match(pattern, value):
        raise ValidationError('Invalid Indian mobile number format. Expected: 10 digits starting with 6-9')

class Customer(models.Model):
    company_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255)
    mobile_number = models.CharField(
        max_length=15, 
        validators=[validate_mobile_number]
    )
    email = models.EmailField()
    gst_number = models.CharField(
        max_length=15, 
        unique=True, 
        validators=[validate_gst_number]
    )
    address = models.TextField()
    branch_location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_migrated = models.BooleanField(default=False)

    def clean(self):
        """Additional validation"""
        super().clean()
        if self.gst_number and Customer.objects.filter(
            gst_number=self.gst_number
        ).exclude(pk=self.pk).exists():
            raise ValidationError({'gst_number': 'This GST number is already registered.'})

    def __str__(self):
        return self.company_name

    class Meta:
        db_table = 'fd_customer'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'

class TermsAndConditions(models.Model):
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'fd_terms_conditions'
        verbose_name = 'Terms and Conditions'
        verbose_name_plural = 'Terms and Conditions'

class WorkOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    work_order_number = models.CharField(max_length=50, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    project_title = models.CharField(max_length=255)
    project_description = models.TextField(blank=True, null=True)
    
    # Financial Fields
    base_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        default=Decimal('0.00')
    )
    gst_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('18.00')
    )
    gst_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00')
    )
    discount = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00')
    )
    discount_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00')
    )
    total_cost = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        default=Decimal('0.00')
    )
    
    # GST Fields
    hsn_code = models.CharField(max_length=10, blank=True, default='998314')
    sac_code = models.CharField(max_length=10, blank=True, default='998314')
    place_of_supply = models.CharField(max_length=100, blank=True, default='Gujarat')
    is_service = models.BooleanField(default=True)
    
    # OLD FIELDS (kept for backward compatibility)
    estimated_hours = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        null=True, 
        blank=True
    )
    hourly_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        null=True, 
        blank=True
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    terms_and_conditions = models.TextField()
    created_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_migrated = models.BooleanField(default=False)

    def generate_work_order_number(self):
        """Generate FDWO-YY-XXXX format work order number"""
        from datetime import datetime
        
        current_year = datetime.now().year
        year_suffix = str(current_year)[-2:]  # Last 2 digits of year
        
        # Find the highest existing work order number for this year
        existing_orders = WorkOrder.objects.filter(
            work_order_number__startswith=f'FDWO-{year_suffix}-'
        ).order_by('-work_order_number')
        
        if existing_orders.exists():
            try:
                # Extract number from FDWO-YY-XXXX format
                last_number = existing_orders.first().work_order_number
                last_sequence = int(last_number.split('-')[-1])
                new_sequence = last_sequence + 1
                
                # If we reach 9999, check for FDWO1 prefix
                if new_sequence > 9999:
                    existing_orders_fdwo1 = WorkOrder.objects.filter(
                        work_order_number__startswith=f'FDWO1-{year_suffix}-'
                    ).order_by('-work_order_number')
                    
                    if existing_orders_fdwo1.exists():
                        last_number_fdwo1 = existing_orders_fdwo1.first().work_order_number
                        last_sequence_fdwo1 = int(last_number_fdwo1.split('-')[-1])
                        new_sequence = last_sequence_fdwo1 + 1
                        prefix = f"FDWO1-{year_suffix}-"
                    else:
                        new_sequence = 1
                        prefix = f"FDWO1-{year_suffix}-"
                else:
                    prefix = f"FDWO-{year_suffix}-"
                    
            except (ValueError, IndexError):
                new_sequence = 1
                prefix = f"FDWO-{year_suffix}-"
        else:
            new_sequence = 1
            prefix = f"FDWO-{year_suffix}-"
            
        return f"{prefix}{new_sequence:04d}"

    def calculate_financials(self):
        """Calculate GST, discount, and total cost automatically with error handling"""
        try:
            base = self.base_amount
            
            # Calculate discount amount
            self.discount_amount = (base * self.discount) / Decimal('100')
            
            # Calculate taxable amount after discount
            taxable_amount = base - self.discount_amount
            
            # Calculate GST amount
            self.gst_amount = (taxable_amount * self.gst_percentage) / Decimal('100')
            
            # Calculate total cost
            self.total_cost = taxable_amount + self.gst_amount
        except (TypeError, ValueError, DecimalException) as e:
            # Set default values on error
            self.discount_amount = Decimal('0.00')
            self.gst_amount = Decimal('0.00')
            self.total_cost = base

    def save(self, *args, **kwargs):
        # Generate work order number if it doesn't exist
        if not self.work_order_number:
            self.work_order_number = self.generate_work_order_number()
        
        # Auto-calculate financials
        self.calculate_financials()
        
        # Save the object
        try:
            super().save(*args, **kwargs)
        except Exception as e:
            # If there's a unique constraint error, generate a new number and try again
            if 'UNIQUE constraint failed' in str(e) and 'work_order_number' in str(e):
                # Generate a temporary unique number with timestamp
                import time
                timestamp = int(time.time())
                self.work_order_number = f"FDWO-TEMP-{timestamp}"
                super().save(*args, **kwargs)
            else:
                raise e

    def __str__(self):
        return self.work_order_number

    class Meta:
        db_table = 'fd_work_order'
        verbose_name = 'Work Order'
        verbose_name_plural = 'Work Orders'

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True)
    work_order = models.OneToOneField(WorkOrder, on_delete=models.CASCADE, related_name='invoice')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    
    # Basic Amount Fields
    base_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00')
    )
    gst_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('18.00')
    )
    gst_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00')
    )
    subtotal = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00')
    )
    total_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        default=Decimal('0.00')
    )
    
    # GST Breakdown Fields
    hsn_code = models.CharField(max_length=10, blank=True, default='998314')
    sac_code = models.CharField(max_length=10, blank=True, default='998314')
    place_of_supply = models.CharField(max_length=100, blank=True, default='Gujarat')
    is_service = models.BooleanField(default=True)
    
    # GST Tax Components
    cgst_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('9.00')
    )
    sgst_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('9.00')
    )
    igst_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    cgst_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    sgst_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    igst_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Payment Fields
    amount_paid = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    balance_due = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Additional Fields
    payment_collected_at_conversion = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    terms_and_conditions = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_migrated = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        from django.db import IntegrityError
        
        # Generate invoice number only for new invoices
        if not self.invoice_number:
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    # Get current financial year
                    today = timezone.now().date()
                    if today.month >= 4:
                        financial_year = f"{today.year}-{today.year + 1}"
                    else:
                        financial_year = f"{today.year - 1}-{today.year}"
                    
                    # Extract last two digits for short format (25-26)
                    year_parts = financial_year.split('-')
                    short_year = f"{year_parts[0][-2:]}{year_parts[1][-2]}"
                    
                    # Find the last invoice for this financial year
                    last_invoice = Invoice.objects.filter(
                        invoice_number__startswith=f"FD{short_year}/I/"
                    ).order_by('-invoice_number').first()
                    
                    if last_invoice and last_invoice.invoice_number:
                        try:
                            # Extract number from format FD25-26/I/0013
                            parts = last_invoice.invoice_number.split('/')
                            if len(parts) >= 3:
                                last_number = int(parts[2])
                                new_number = last_number + 1
                            else:
                                new_number = 1
                        except (ValueError, IndexError):
                            new_number = 1
                    else:
                        # Start from 0013 for continuity as requested
                        new_number = 13
                        
                    self.invoice_number = f"FD{short_year}/I/{new_number:04d}"
                    
                    # Calculate GST breakup before saving
                    self.calculate_gst_breakup()
                    
                    # Calculate balance due
                    self.balance_due = self.total_amount - self.amount_paid
                    
                    # Update status based on payment
                    if self.balance_due == 0 and self.total_amount > 0:
                        self.status = 'paid'
                    elif self.amount_paid > 0 and self.balance_due > 0:
                        self.status = 'partially_paid'
                    elif self.balance_due > 0 and self.due_date < timezone.now().date():
                        self.status = 'overdue'
                    elif self.status == 'draft' and self.invoice_number:
                        self.status = 'sent'
                        
                    super().save(*args, **kwargs)
                    break  # Success, exit loop
                    
                except IntegrityError:
                    if attempt == max_attempts - 1:
                        raise
                    # Regenerate number and try again
                    continue
        else:
            # For existing invoices, just save normally
            super().save(*args, **kwargs)

    def calculate_gst_breakup(self):
        """Calculate CGST, SGST, IGST based on place of supply"""
        try:
            # Use subtotal for GST calculation
            taxable_amount = self.subtotal
            
            # Simple logic: If place of supply is same as company state, use CGST+SGST
            # Assuming company is in Gujarat
            if self.place_of_supply.lower() == 'gujarat':
                self.cgst_amount = (taxable_amount * self.cgst_rate) / Decimal('100')
                self.sgst_amount = (taxable_amount * self.sgst_rate) / Decimal('100')
                self.igst_amount = Decimal('0.00')
                self.igst_rate = Decimal('0.00')
            else:
                # For inter-state, use IGST (18%)
                self.igst_rate = Decimal('18.00')
                self.igst_amount = (taxable_amount * self.igst_rate) / Decimal('100')
                self.cgst_amount = Decimal('0.00')
                self.sgst_amount = Decimal('0.00')
                self.cgst_rate = Decimal('0.00')
                self.sgst_rate = Decimal('0.00')
        except (TypeError, ValueError, DecimalException):
            # Set default values on error
            self.cgst_amount = Decimal('0.00')
            self.sgst_amount = Decimal('0.00')
            self.igst_amount = Decimal('0.00')

    def get_gst_breakup_display(self):
        """Return GST breakup for display purposes"""
        if self.place_of_supply.lower() == 'gujarat':
            return {
                'cgst': {'rate': self.cgst_rate, 'amount': self.cgst_amount},
                'sgst': {'rate': self.sgst_rate, 'amount': self.sgst_amount},
                'igst': {'rate': self.igst_rate, 'amount': self.igst_amount}
            }
        else:
            return {
                'igst': {'rate': self.igst_rate, 'amount': self.igst_amount},
                'cgst': {'rate': self.cgst_rate, 'amount': self.cgst_amount},
                'sgst': {'rate': self.sgst_rate, 'amount': self.sgst_amount}
            }

    def get_payment_summary(self):
        """Get payment summary for display"""
        payments = self.payments.all()
        return {
            'total_paid': self.amount_paid,
            'balance_due': self.balance_due,
            'payment_count': payments.count(),
            'payments': payments.order_by('-payment_date')
        }

    def get_status_display_color(self):
        """Return Bootstrap color class for status"""
        status_colors = {
            'draft': 'secondary',
            'sent': 'info',
            'partially_paid': 'warning',
            'paid': 'success',
            'overdue': 'danger',
            'cancelled': 'dark'
        }
        return status_colors.get(self.status, 'secondary')

    def __str__(self):
        return self.invoice_number

    class Meta:
        db_table = 'fd_invoice'
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('upi', 'UPI'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='completed')
    created_at = models.DateTimeField(auto_now_add=True)
    is_migrated = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update invoice payment status
        if self.status == 'completed':
            self.update_invoice_payment_status()

    def update_invoice_payment_status(self):
        """Update the parent invoice's payment status"""
        try:
            invoice = self.invoice
            total_paid = sum(
                payment.amount for payment in invoice.payments.filter(status='completed')
            )
            invoice.amount_paid = total_paid
            invoice.balance_due = invoice.total_amount - total_paid
            
            # Update invoice status based on payment
            if invoice.balance_due == 0:
                invoice.status = 'paid'
            elif total_paid > 0:
                invoice.status = 'partially_paid'
            elif invoice.due_date < timezone.now().date():
                invoice.status = 'overdue'
                
            invoice.save()
        except Exception as e:
            # Log error but don't break the payment save
            print(f"Error updating invoice payment status: {e}")

    def get_payment_method_display(self):
        """Get human-readable payment method"""
        return dict(self.PAYMENT_METHODS).get(self.payment_method, self.payment_method)

    def get_status_display_color(self):
        """Return Bootstrap color class for status"""
        status_colors = {
            'pending': 'warning',
            'completed': 'success',
            'failed': 'danger',
            'refunded': 'info'
        }
        return status_colors.get(self.status, 'secondary')

    def __str__(self):
        return f"Payment #{self.id} - ₹{self.amount} - {self.payment_date}"

    class Meta:
        db_table = 'fd_payment'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-payment_date', '-created_at']

class EmailConfiguration(models.Model):
    name = models.CharField(max_length=255, default='Default')
    days_after_invoice = models.IntegerField(
        default=7,
        help_text="Days after invoice creation to send first reminder"
    )
    reminder_frequency = models.IntegerField(
        default=3,
        help_text="Frequency in days between reminders"
    )
    is_active = models.BooleanField(default=True)
    max_reminders = models.IntegerField(
        default=5,
        help_text="Maximum number of reminders to send"
    )
    email_subject = models.CharField(
        max_length=255, 
        default="Payment Reminder: Invoice {invoice_number}"
    )
    email_template = models.TextField(
        default="""Dear {customer_name},

This is a friendly reminder that your invoice is pending payment.

Invoice Number: {invoice_number}
Total Amount: ₹{total_amount}
Balance Due: ₹{balance_due}
Project: {project_title}
Due Date: {due_date}

Please make the payment at your earliest convenience.

Best regards,
FolkDrive Team"""
    )
    
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'fd_email_config'
        verbose_name = 'Email Configuration'
        verbose_name_plural = 'Email Configurations'

class EmailLog(models.Model):
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='sent')
    error_message = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Email to {self.recipient} at {self.sent_at}"

    class Meta:
        db_table = 'fd_email_log'
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'

class PaymentReminderLog(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    sent_date = models.DateTimeField(auto_now_add=True)
    reminder_number = models.IntegerField()
    status = models.CharField(max_length=20, default='sent')
    
    def __str__(self):
        return f"Reminder {self.reminder_number} for {self.invoice.invoice_number}"

    class Meta:
        db_table = 'fd_payment_reminder_log'
        verbose_name = 'Payment Reminder Log'
        verbose_name_plural = 'Payment Reminder Logs'

class CompanySettings(models.Model):
    company_name = models.CharField(max_length=255, default='FolkDrive')
    legal_name = models.CharField(max_length=255, default='FolkDrive Solutions')
    address = models.TextField(default='Your Company Address')
    city = models.CharField(max_length=100, default='City')
    state = models.CharField(max_length=100, default='Gujarat')
    pincode = models.CharField(max_length=10, default='380001')
    phone = models.CharField(max_length=15, default='+91-XXXXXXXXXX')
    email = models.EmailField(default='info@folkdrive.com')
    website = models.URLField(default='https://folkdrive.com')
    
    # GST Details
    gst_number = models.CharField(max_length=15, default='GSTINXXXXXXXXXXXXX')
    pan_number = models.CharField(max_length=10, default='XXXXXXXXXX')
    state_code = models.CharField(max_length=2, default='24')
    
    # Bank Details
    bank_name = models.CharField(max_length=255, default='Bank Name')
    account_number = models.CharField(max_length=20, default='XXXXXXXXXXXX')
    account_holder = models.CharField(max_length=255, default='FolkDrive Solutions')
    ifsc_code = models.CharField(max_length=11, default='XXXX0000000')
    branch = models.CharField(max_length=100, default='Branch Name')
    
    # Invoice Settings
    invoice_terms = models.TextField(default='Payment due within 30 days of invoice date.')
    invoice_footer = models.TextField(default='Thank you for your business!')
    
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Company Settings - {self.company_name}"

    class Meta:
        db_table = 'fd_company_settings'
        verbose_name = 'Company Setting'
        verbose_name_plural = 'Company Settings'

# Additional helper models for better organization
class ProjectCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'fd_project_category'
        verbose_name = 'Project Category'
        verbose_name_plural = 'Project Categories'

class TaxConfiguration(models.Model):
    name = models.CharField(max_length=100, default='GST')
    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('9.00'))
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('9.00'))
    igst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'))
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.name} - {self.effective_from}"

    class Meta:
        db_table = 'fd_tax_configuration'
        verbose_name = 'Tax Configuration'
        verbose_name_plural = 'Tax Configurations'