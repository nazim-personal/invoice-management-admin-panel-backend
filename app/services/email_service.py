import threading
from flask import current_app, render_template
from flask_mail import Message
from flask_jwt_extended import get_jwt_identity
from app.database.models.user import User

class EmailService:
    @staticmethod
    def send_async_email(app, msg):
        with app.app_context():
            try:
                from app import mail
                print(f"[EMAIL] Sending email to {msg.recipients}...")
                mail.send(msg)
                print(f"[EMAIL] Email sent successfully!")
            except Exception as e:
                print(f"[EMAIL ERROR] Failed to send email: {e}")
                import traceback
                traceback.print_exc()

    @staticmethod
    def send_email(subject, recipients, template, sender=None, **kwargs):
        print(f"[EMAIL] Preparing email: {subject}")
        print(f"[EMAIL] Recipients: {recipients}")
        print(f"[EMAIL] Template: {template}")
        print(f"[EMAIL] Sender: {sender}")

        app = current_app._get_current_object()
        msg = Message(subject, recipients=recipients, sender=sender)
        msg.html = render_template(template, **kwargs)

        # Use threading for async sending
        thr = threading.Thread(target=EmailService.send_async_email, args=[app, msg])
        thr.start()
        print(f"[EMAIL] Email thread started")

    @staticmethod
    def get_sender_for_invoice(invoice):
        try:
            # invoice can be a dict or object. Handle both.
            user_id = invoice.get('user_id') if isinstance(invoice, dict) else invoice.user_id
            if user_id:
                user = User.find_by_id(user_id)
                if user:
                    return user.email or user.company_email
        except Exception:
            pass
        return None

    @staticmethod
    def should_send_notification(user_id, notification_type):
        """
        Check if a notification should be sent based on user settings.

        Args:
            user_id: The user's ID
            notification_type: One of 'invoice_created', 'payment_received', 'invoice_overdue'

        Returns:
            Boolean indicating if notification should be sent
        """
        try:
            from app.database.models.notification_settings import NotificationSettings
            return NotificationSettings.is_notification_enabled(user_id, notification_type)
        except Exception as e:
            print(f"Error checking notification settings: {e}")
            # Default to True if there's an error (fail-open)
            return True

    @staticmethod
    def send_invoice_created_email(invoice, customer):
        print(f"[EMAIL] Attempting to send invoice created email...")
        print(f"[EMAIL] Customer email: {customer.email}")
        print(f"[EMAIL] Invoice: {invoice.get('invoice_number')}")

        if not customer.email:
            print(f"[EMAIL] No customer email - skipping")
            return

        # Check if user has enabled invoice_created notifications
        user_id = invoice.get('user_id') if isinstance(invoice, dict) else invoice.user_id
        print(f"[EMAIL] User ID: {user_id}")

        if not EmailService.should_send_notification(user_id, 'invoice_created'):
            print(f"[EMAIL] Invoice created notification disabled for user {user_id}")
            return

        print(f"[EMAIL] Notification enabled - preparing email...")
        subject = f"Invoice #{invoice['invoice_number']} Created"
        sender = EmailService.get_sender_for_invoice(invoice)
        print(f"[EMAIL] Sender: {sender}")
        print(f"[EMAIL] Recipient: {customer.email}")

        EmailService.send_email(
            subject,
            [customer.email],
            'email/invoice_created.html',
            sender=sender,
            invoice=invoice,
            customer=customer
        )
        print(f"[EMAIL] Email queued for sending")

    @staticmethod
    def send_payment_received_email(payment, invoice, customer):
        if not customer.email:
            return

        # Check if user has enabled payment_received notifications
        # Check if user has enabled payment_received notifications
        user_id = invoice.user_id if hasattr(invoice, 'user_id') else invoice.get('user_id')
        if not EmailService.should_send_notification(user_id, 'payment_received'):
            print(f"Payment received notification disabled for user {user_id}")
            return

        invoice_number = invoice.invoice_number if hasattr(invoice, 'invoice_number') else invoice.get('invoice_number')
        subject = f"Payment Received for Invoice #{invoice_number}"
        sender = EmailService.get_sender_for_invoice(invoice)

        EmailService.send_email(
            subject,
            [customer.email],
            'email/payment_received.html',
            sender=sender,
            payment=payment,
            invoice=invoice,
            customer=customer
        )

    @staticmethod
    def send_invoice_overdue_email(invoice, customer, days_overdue):
        if not customer.email:
            return

        # Check if user has enabled invoice_overdue notifications
        user_id = invoice.get('user_id') if isinstance(invoice, dict) else invoice.user_id
        if not EmailService.should_send_notification(user_id, 'invoice_overdue'):
            print(f"Invoice overdue notification disabled for user {user_id}")
            return

        subject = f"Overdue Invoice Reminder - Invoice #{invoice.invoice_number}"
        sender = EmailService.get_sender_for_invoice(invoice)

        EmailService.send_email(
            subject,
            [customer.email],
            'email/invoice_overdue.html',
            sender=sender,
            invoice=invoice,
            customer=customer,
            days_overdue=days_overdue
        )

email_service = EmailService()
