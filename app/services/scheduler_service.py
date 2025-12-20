import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, app=None):
        self.scheduler = BackgroundScheduler()
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        # Schedule overdue invoice check to run daily at 9 AM
        self.scheduler.add_job(
            func=self.check_overdue_invoices,
            trigger=CronTrigger(hour=9, minute=0),
            id='check_overdue_invoices',
            name='Check and notify overdue invoices',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("Scheduler started - Overdue invoice check scheduled for 9:00 AM daily")

    def check_overdue_invoices(self):
        """
        Check for overdue invoices and send email notifications
        This runs as a scheduled background task
        """
        if not self.app:
            logger.error("App context not available for scheduler")
            return

        with self.app.app_context():
            try:
                from app.database.models.invoice import Invoice
                from app.database.models.customer import Customer
                from app.services.email_service import email_service

                logger.info("Starting overdue invoice check...")
                overdue_invoices = Invoice.find_overdue_invoices()

                if not overdue_invoices:
                    logger.info("No overdue invoices found")
                    return

                sent_count = 0
                for invoice in overdue_invoices:
                    try:
                        # Get customer details
                        customer = Customer.find_by_id(invoice.customer_id)
                        if not customer or not customer.email:
                            logger.warning(f"Skipping invoice {invoice.invoice_number} - no customer email")
                            continue

                        days_overdue = getattr(invoice, 'days_overdue', 0)

                        # Send overdue notification
                        email_service.send_invoice_overdue_email(
                            invoice.to_dict(),
                            customer,
                            days_overdue
                        )
                        sent_count += 1
                        logger.info(f"Sent overdue notification for invoice {invoice.invoice_number} to {customer.email}")

                    except Exception as e:
                        logger.error(f"Failed to send overdue email for invoice {invoice.invoice_number}: {str(e)}")
                        continue

                logger.info(f"Overdue invoice check completed. Sent {sent_count} notifications out of {len(overdue_invoices)} overdue invoices")

            except Exception as e:
                logger.error(f"Error during overdue invoice check: {str(e)}")

    def shutdown(self):
        """Shutdown the scheduler gracefully"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shut down")

# Global scheduler instance
scheduler_service = SchedulerService()
