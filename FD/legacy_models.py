# FD/legacy_models.py
from django.db import models

class LegacyCustomer(models.Model):
    _legacy = True  # Mark as legacy model
    
    id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255)
    mobile_number = models.CharField(max_length=15)
    email = models.EmailField()
    gst_number = models.CharField(max_length=15)
    address = models.TextField()
    branch_location = models.CharField(max_length=255)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'customers'  # Your actual MySQL table name
        managed = False

class LegacyWorkOrder(models.Model):
    _legacy = True  # Mark as legacy model
    
    id = models.AutoField(primary_key=True)
    work_order_number = models.CharField(max_length=50)
    customer_id = models.IntegerField()
    project_title = models.CharField(max_length=255)
    project_description = models.TextField()
    total_cost = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'daily_orders'  # Your actual MySQL table name
        managed = False

class LegacyInvoice(models.Model):
    _legacy = True  # Mark as legacy model
    
    id = models.AutoField(primary_key=True)
    invoice_number = models.CharField(max_length=50)
    work_order_id = models.IntegerField()
    customer_id = models.IntegerField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2)
    balance_due = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'invoices'  # Your actual MySQL table name
        managed = False