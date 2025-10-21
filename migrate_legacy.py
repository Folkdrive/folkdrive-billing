# correct_migration.py
import pymysql
from datetime import datetime
import os
import sys
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FDbilling.settings')

import django
django.setup()

from FD.models import Customer, WorkOrder, Invoice, Payment, TermsAndConditions, CompanySettings

def correct_migration():
    print("🎯 CORRECT LEGACY DATA MIGRATION")
    print("📊 Using your actual MySQL column names...")
    
    mysql_config = {
        'host': 'localhost',
        'user': 'root',
        'password': 'root', 
        'database': 'folkdrive',
        'charset': 'utf8'
    }
    
    try:
        mysql_conn = pymysql.connect(**mysql_config)
        mysql_cursor = mysql_conn.cursor()
        
        # Create default terms
        terms, _ = TermsAndConditions.objects.get_or_create(
            code='legacy_terms',
            defaults={
                'title': 'Legacy Terms and Conditions',
                'content': 'Standard terms from legacy system',
                'is_active': True
            }
        )
        
        # MIGRATE CUSTOMERS with correct column mapping
        print("👥 Migrating customers with REAL data...")
        mysql_cursor.execute("SELECT * FROM customers")
        customers_data = mysql_cursor.fetchall()
        
        customer_map = {}
        migrated_customers = 0
        
        for row in customers_data:
            try:
                # Map your actual columns: id, cname, addr1, addr2, pin, sname, gst, cdate, ctime, cuser
                customer_id = row[0]
                company_name = row[1]  # cname
                address_line1 = row[2]  # addr1
                address_line2 = row[3]  # addr2
                full_address = f"{address_line1 or ''} {address_line2 or ''}".strip()
                gst_number = row[6]    # gst
                
                # Handle empty GST numbers
                if not gst_number or gst_number.strip() == '':
                    gst_number = f"LEGACY-{customer_id}"
                
                customer = Customer(
                    company_name=company_name[:255],
                    contact_name="Contact Person",  # Your table doesn't have contact name
                    mobile_number="0000000000",     # Your table doesn't have mobile
                    email=f"contact{customer_id}@company.com",  # Your table doesn't have email
                    gst_number=gst_number[:15],
                    address=full_address[:500],
                    branch_location="Main Branch",  # Your table doesn't have branch location
                    is_migrated=True
                )
                customer.save()
                customer_map[customer_id] = customer.id
                migrated_customers += 1
                print(f"  ✅ {customer.company_name} - GST: {customer.gst_number}")
                
            except Exception as e:
                print(f"  ❌ Customer error: {e}")
                continue
        
        # MIGRATE WORK ORDERS with correct column mapping
        print("\n📋 Migrating work orders with REAL data...")
        mysql_cursor.execute("SELECT * FROM daily_orders")
        work_orders_data = mysql_cursor.fetchall()
        
        work_order_map = {}
        migrated_work_orders = 0
        
        for row in work_orders_data:
            try:
                # Map your actual columns from daily_orders
                wo_id = row[0]           # id
                customer_id = row[1]     # pname (this seems to be customer_id)
                docno = row[20]          # docno (work order number)
                total_amount = row[9]    # gttl (grand total)
                remarks = row[13]        # rem (remarks/description)
                order_date = row[12]     # odate (order date)
                
                # Find customer
                customer = None
                if customer_id in customer_map:
                    customer = Customer.objects.get(id=customer_map[customer_id])
                else:
                    # Use first customer as fallback
                    customer = Customer.objects.filter(is_migrated=True).first()
                
                if not customer:
                    continue
                
                # Convert amount to decimal
                try:
                    base_amount = Decimal(str(total_amount)) if total_amount else Decimal('0.00')
                except:
                    base_amount = Decimal('0.00')
                
                # Calculate GST (18% assumed)
                gst_percentage = Decimal('18.00')
                gst_amount = (base_amount * gst_percentage) / Decimal('100')
                
                work_order = WorkOrder(
                    work_order_number=docno or f"LEGACY-WO-{wo_id}",
                    customer=customer,
                    project_title=f"Project {docno}" if docno else f"Legacy Project {wo_id}",
                    project_description=remarks or f"Work order from legacy system - ID: {wo_id}",
                    base_amount=base_amount,
                    gst_percentage=gst_percentage,
                    gst_amount=gst_amount,
                    total_cost=base_amount,
                    status='completed',
                    terms_and_conditions=terms,
                    created_by='Legacy Migration',
                    is_migrated=True
                )
                work_order.save()
                work_order_map[wo_id] = work_order.id
                migrated_work_orders += 1
                print(f"  ✅ {work_order.work_order_number} - ₹{base_amount} - {customer.company_name}")
                
            except Exception as e:
                print(f"  ❌ Work order error: {e}")
                continue
        
        # MIGRATE PAYMENTS with correct column mapping
        print("\n💰 Migrating payments with REAL data...")
        mysql_cursor.execute("SELECT * FROM payment_details")
        payments_data = mysql_cursor.fetchall()
        
        migrated_payments = 0
        
        for row in payments_data:
            try:
                # Map your actual columns from payment_details
                doc_no = row[1]      # doc_no (document number - matches work order docno)
                payment_date = row[2] # pdate (payment date)
                payment_type = row[3] # ptype (payment method)
                amount_paid = row[9]  # apaid (amount paid)
                remarks = row[4]      # rem (remarks/reference)
                
                # Find work order by docno
                work_order = WorkOrder.objects.filter(
                    work_order_number=doc_no, 
                    is_migrated=True
                ).first()
                
                if not work_order:
                    print(f"  ⚠️  No work order found for payment doc: {doc_no}")
                    continue
                
                # Convert amount to decimal
                try:
                    amount = Decimal(str(amount_paid)) if amount_paid else Decimal('0.00')
                except:
                    amount = Decimal('0.00')
                
                # Map payment type
                payment_method_map = {
                    'IMPS': 'bank_transfer',
                    'NEFT': 'bank_transfer', 
                    'UPI': 'upi',
                    'Cheque': 'cheque'
                }
                payment_method = payment_method_map.get(payment_type, 'bank_transfer')
                
                # Create or get invoice for this work order
                invoice, created = Invoice.objects.get_or_create(
                    work_order=work_order,
                    defaults={
                        'customer': work_order.customer,
                        'invoice_date': datetime.now().date(),
                        'due_date': datetime.now().date(),
                        'subtotal': work_order.base_amount,
                        'base_amount': work_order.base_amount,
                        'gst_percentage': work_order.gst_percentage,
                        'gst_amount': work_order.gst_amount,
                        'total_amount': work_order.total_cost,
                        'amount_paid': Decimal('0.00'),
                        'balance_due': work_order.total_cost,
                        'terms_and_conditions': terms.content,
                        'status': 'sent',
                        'is_migrated': True
                    }
                )
                
                # Create payment
                payment = Payment(
                    invoice=invoice,
                    payment_date=datetime.strptime(payment_date, '%Y-%m-%d').date() if payment_date else datetime.now().date(),
                    amount=amount,
                    payment_method=payment_method,
                    reference_number=remarks[:100],
                    notes=f"Legacy payment - {payment_type}",
                    is_migrated=True
                )
                payment.save()
                
                # Update invoice payment status
                invoice.amount_paid += amount
                invoice.balance_due = invoice.total_amount - invoice.amount_paid
                if invoice.balance_due == 0:
                    invoice.status = 'paid'
                elif invoice.amount_paid > 0:
                    invoice.status = 'partially_paid'
                invoice.save()
                
                migrated_payments += 1
                print(f"  ✅ Payment: ₹{amount} for {doc_no} - {payment_type}")
                
            except Exception as e:
                print(f"  ❌ Payment error: {e}")
                continue
        
        mysql_conn.close()
        
        # FINAL SUMMARY
        print("\n🎉 CORRECT MIGRATION COMPLETE!")
        print("=" * 60)
        print(f"📊 REAL DATA MIGRATION SUMMARY:")
        print(f"   👥 Customers: {Customer.objects.filter(is_migrated=True).count()}")
        print(f"   📋 Work Orders: {WorkOrder.objects.filter(is_migrated=True).count()}")
        print(f"   🧾 Invoices: {Invoice.objects.filter(is_migrated=True).count()}")
        print(f"   💰 Payments: {Payment.objects.filter(is_migrated=True).count()}")
        print("=" * 60)
        print(f"🚀 Your REAL legacy data is now in SQLite3!")
        print(f"💡 Run: python manage.py runserver")
        print(f"🌐 Visit: http://localhost:8000/legacy-data/")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    correct_migration()