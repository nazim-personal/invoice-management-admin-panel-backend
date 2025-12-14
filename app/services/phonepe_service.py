import os
import base64
import hashlib
import json
import requests
from typing import Dict, Any, Optional
from decimal import Decimal

class PhonePeService:
    """Service class for PhonePe Payment Gateway integration."""

    def __init__(self):
        self.merchant_id = os.getenv('PHONEPE_MERCHANT_ID')
        self.salt_key = os.getenv('PHONEPE_SALT_KEY')
        self.salt_index = os.getenv('PHONEPE_SALT_INDEX', '1')
        self.api_url = os.getenv('PHONEPE_API_URL', 'https://api-preprod.phonepe.com/apis/pg-sandbox')
        self.redirect_url = os.getenv('PHONEPE_REDIRECT_URL', 'http://localhost:3000/payment/success')
        self.callback_url = os.getenv('PHONEPE_CALLBACK_URL')

        if not all([self.merchant_id, self.salt_key, self.callback_url]):
            raise ValueError("PhonePe credentials not configured. Check environment variables.")

    def generate_signature(self, payload: str) -> str:
        """
        Generate X-VERIFY signature for PhonePe API requests.
        Formula: SHA256(base64_payload + "/pg/v1/pay" + salt_key) + ### + salt_index
        """
        string_to_hash = payload + "/pg/v1/pay" + self.salt_key
        sha256_hash = hashlib.sha256(string_to_hash.encode()).hexdigest()
        return f"{sha256_hash}###{self.salt_index}"

    def verify_webhook_signature(self, x_verify_header: str, response_payload: str) -> bool:
        """
        Verify webhook signature from PhonePe.
        Formula: SHA256(base64_response + salt_key) + ### + salt_index
        """
        try:
            string_to_hash = response_payload + self.salt_key
            calculated_hash = hashlib.sha256(string_to_hash.encode()).hexdigest()
            calculated_signature = f"{calculated_hash}###{self.salt_index}"
            return calculated_signature == x_verify_header
        except Exception:
            return False

    def initiate_payment(
        self,
        invoice_id: str,
        amount: Decimal,
        customer_phone: str,
        customer_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initiate a PhonePe payment transaction.

        Args:
            invoice_id: Unique invoice identifier
            amount: Payment amount in rupees
            customer_phone: Customer's mobile number
            customer_name: Customer's name (optional)

        Returns:
            Dict containing payment URL and transaction ID
        """
        # Convert amount to paise (PhonePe uses paise)
        amount_in_paise = int(amount * 100)

        # Generate unique merchant transaction ID
        merchant_transaction_id = f"INV_{invoice_id}_{int(os.urandom(4).hex(), 16)}"

        # Prepare payment request payload
        payload_data = {
            "merchantId": self.merchant_id,
            "merchantTransactionId": merchant_transaction_id,
            "merchantUserId": f"USER_{customer_phone[-10:]}",
            "amount": amount_in_paise,
            "redirectUrl": f"{self.redirect_url}?invoice_id={invoice_id}",
            "redirectMode": "POST",
            "callbackUrl": self.callback_url,
            "mobileNumber": customer_phone,
            "paymentInstrument": {
                "type": "PAY_PAGE"
            }
        }

        # Add customer name if provided
        if customer_name:
            payload_data["merchantUserId"] = f"USER_{customer_name.replace(' ', '_')}"

        # Encode payload to base64
        payload_json = json.dumps(payload_data)
        base64_payload = base64.b64encode(payload_json.encode()).decode()

        # Generate signature
        x_verify = self.generate_signature(base64_payload)

        # Prepare API request
        headers = {
            "Content-Type": "application/json",
            "X-VERIFY": x_verify
        }

        request_data = {
            "request": base64_payload
        }

        try:
            # Make API call to PhonePe
            response = requests.post(
                f"{self.api_url}/pg/v1/pay",
                json=request_data,
                headers=headers,
                timeout=30
            )

            response_data = response.json()

            if response_data.get('success'):
                return {
                    'success': True,
                    'payment_url': response_data['data']['instrumentResponse']['redirectInfo']['url'],
                    'transaction_id': merchant_transaction_id,
                    'phonepe_transaction_id': response_data['data'].get('merchantTransactionId'),
                    'message': 'Payment initiated successfully'
                }
            else:
                return {
                    'success': False,
                    'message': response_data.get('message', 'Payment initiation failed'),
                    'error_code': response_data.get('code')
                }

        except requests.RequestException as e:
            return {
                'success': False,
                'message': f'PhonePe API error: {str(e)}'
            }

    def check_payment_status(self, merchant_transaction_id: str) -> Dict[str, Any]:
        """
        Check the status of a PhonePe transaction.

        Args:
            merchant_transaction_id: The merchant transaction ID

        Returns:
            Dict containing payment status and details
        """
        # Generate signature for status check
        string_to_hash = f"/pg/v1/status/{self.merchant_id}/{merchant_transaction_id}{self.salt_key}"
        sha256_hash = hashlib.sha256(string_to_hash.encode()).hexdigest()
        x_verify = f"{sha256_hash}###{self.salt_index}"

        headers = {
            "Content-Type": "application/json",
            "X-VERIFY": x_verify
        }

        try:
            response = requests.get(
                f"{self.api_url}/pg/v1/status/{self.merchant_id}/{merchant_transaction_id}",
                headers=headers,
                timeout=30
            )

            response_data = response.json()

            if response_data.get('success'):
                payment_data = response_data.get('data', {})
                return {
                    'success': True,
                    'status': payment_data.get('state'),  # SUCCESS, FAILED, PENDING
                    'amount': payment_data.get('amount', 0) / 100,  # Convert paise to rupees
                    'transaction_id': payment_data.get('merchantTransactionId'),
                    'phonepe_transaction_id': payment_data.get('transactionId'),
                    'payment_instrument': payment_data.get('paymentInstrument', {}),
                    'response_code': payment_data.get('responseCode'),
                    'raw_response': response_data
                }
            else:
                return {
                    'success': False,
                    'message': response_data.get('message', 'Status check failed'),
                    'error_code': response_data.get('code')
                }

        except requests.RequestException as e:
            return {
                'success': False,
                'message': f'PhonePe API error: {str(e)}'
            }


# Singleton instance
phonepe_service = PhonePeService()
