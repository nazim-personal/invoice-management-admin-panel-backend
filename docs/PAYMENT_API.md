# Payment & Webhook API Documentation for UI

## Base URL
```
http://localhost:5001/api
```

---

## Authentication
All endpoints (except webhooks) require JWT authentication:
```
Authorization: Bearer <access_token>
```

---

## Payment Endpoints

### 1. Get All Payments
**GET** `/payments/`

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 10)

**Response:**
```json
{
  "success": true,
  "result": [
    {
      "id": "payment_id",
      "invoice_id": "invoice_id",
      "amount": "100.00",
      "payment_date": "2024-12-14",
      "method": "upi",
      "reference_no": "UPI123456",
      "created_at": "2024-12-14T10:30:00"
    }
  ],
  "meta": {
    "total": 50,
    "page": 1,
    "per_page": 10
  }
}
```

---

### 2. Search Payments
**GET** `/payments/search/`

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `q` (optional): General search (searches reference_no and method)
- `method` (optional): Filter by payment method (`cash`, `card`, `upi`, `bank_transfer`)
- `reference_no` (optional): Search by reference number
- `start_date` (optional): Filter from date (YYYY-MM-DD)
- `end_date` (optional): Filter to date (YYYY-MM-DD)
- `page` (optional): Page number
- `per_page` (optional): Items per page

**Example Requests:**
```bash
# Search by method
GET /payments/search/?method=upi

# Search by date range
GET /payments/search/?start_date=2024-01-01&end_date=2024-12-31

# Combined filters
GET /payments/search/?method=upi&start_date=2024-01-01&reference_no=PAY
```

**Response:**
```json
{
  "success": true,
  "result": [
    {
      "id": "payment_id",
      "invoice_id": "invoice_id",
      "amount": "100.00",
      "payment_date": "2024-12-14",
      "method": "upi",
      "reference_no": "UPI123456"
    }
  ],
  "meta": {
    "total": 25,
    "page": 1,
    "per_page": 10
  }
}
```

---

### 3. Get Payment Details
**GET** `/payments/<payment_id>/`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "result": {
    "id": "payment_id",
    "invoice_id": "invoice_id",
    "amount": "100.00",
    "payment_date": "2024-12-14",
    "method": "upi",
    "reference_no": "UPI123456",
    "transaction_id": "INV_123_abc",
    "payment_gateway": "phonepe",
    "invoice_number": "INV-2024-001",
    "invoice_total": "1000.00",
    "customer_id": "customer_id",
    "customer_name": "John Doe",
    "customer_email": "john@example.com"
  }
}
```

---

### 4. Get Payments for Invoice
**GET** `/invoices/<invoice_id>/payments/`

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "result": [
    {
      "id": "payment_id",
      "invoice_id": "invoice_id",
      "amount": "100.00",
      "payment_date": "2024-12-14",
      "method": "upi",
      "reference_no": "UPI123456"
    }
  ],
  "meta": {
    "total": 3,
    "page": 1,
    "per_page": 10
  }
}
```

---

### 5. Record Manual Payment
**POST** `/invoices/<invoice_id>/pay/`

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "amount": "100.00",
  "method": "upi",
  "reference_no": "UPI123456"
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "id": "payment_id",
    "invoice_id": "invoice_id",
    "amount": "100.00",
    "method": "upi",
    "reference_no": "UPI123456"
  },
  "message": "Payment recorded successfully"
}
```

---

## PhonePe Payment Gateway

### 6. Initiate PhonePe Payment
**POST** `/invoices/<invoice_id>/phonepe-payment/`

**Headers:**
```
Authorization: Bearer <token>
```

**Description:**
Initiates a PhonePe payment for the invoice. Returns a payment URL to redirect the customer.

**Response:**
```json
{
  "success": true,
  "result": {
    "payment_url": "https://mercury-uat.phonepe.com/transact/pg?token=...",
    "transaction_id": "INV_invoice123_abc123",
    "amount": 1000.00
  },
  "message": "PhonePe payment initiated successfully"
}
```

**UI Flow:**
1. User clicks "Pay with PhonePe" button
2. Frontend calls this endpoint
3. Backend returns `payment_url`
4. Redirect user to `payment_url`
5. User completes payment on PhonePe
6. PhonePe redirects back to your `PHONEPE_REDIRECT_URL`
7. Webhook automatically updates invoice (no action needed from UI)

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "phonepe_error",
    "message": "Failed to initiate PhonePe payment",
    "details": "MERCHANT_NOT_FOUND"
  }
}
```

---

## Webhook Endpoint (Backend Only)

### 7. PhonePe Webhook
**POST** `/webhooks/phonepe/`

**⚠️ Important:** This endpoint is called automatically by PhonePe servers. **DO NOT call this from UI.**

**Headers:**
```
X-VERIFY: <signature>
Content-Type: application/json
```

**Request Body:**
```json
{
  "response": "base64_encoded_payment_data"
}
```

**What Happens:**
1. PhonePe sends payment status to this endpoint
2. Backend verifies signature
3. Backend records payment automatically
4. Invoice status updated to "Paid"
5. Activity log created

**UI Handling:**
After payment redirect, poll the invoice status or use WebSocket to get real-time updates.

---

## Payment Methods

Supported payment methods:
- `cash` - Cash payment
- `card` - Card payment
- `upi` - UPI payment (manual or PhonePe)
- `bank_transfer` - Bank transfer

---

## Payment Status Flow

```
1. Invoice Created (status: "Pending")
   ↓
2. User initiates PhonePe payment
   ↓
3. User completes payment on PhonePe
   ↓
4. Webhook receives confirmation
   ↓
5. Payment recorded automatically
   ↓
6. Invoice status updated:
   - "Partially Paid" (if amount < total)
   - "Paid" (if amount >= total)
```

---

## UI Implementation Examples

### Example 1: Initiate PhonePe Payment

```javascript
async function initiatePhonePePayment(invoiceId) {
  try {
    const response = await fetch(
      `http://localhost:5001/api/invoices/${invoiceId}/phonepe-payment/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        }
      }
    );

    const data = await response.json();

    if (data.success) {
      // Redirect user to PhonePe payment page
      window.location.href = data.result.payment_url;
    } else {
      alert('Payment initiation failed: ' + data.error.message);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}
```

### Example 2: Search Payments

```javascript
async function searchPayments(filters) {
  const params = new URLSearchParams();

  if (filters.method) params.append('method', filters.method);
  if (filters.startDate) params.append('start_date', filters.startDate);
  if (filters.endDate) params.append('end_date', filters.endDate);
  if (filters.page) params.append('page', filters.page);

  const response = await fetch(
    `http://localhost:5001/api/payments/search/?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      }
    }
  );

  return await response.json();
}

// Usage
const payments = await searchPayments({
  method: 'upi',
  startDate: '2024-01-01',
  endDate: '2024-12-31',
  page: 1
});
```

### Example 3: Handle Payment Redirect

```javascript
// On payment success redirect page
function handlePaymentRedirect() {
  const urlParams = new URLSearchParams(window.location.search);
  const invoiceId = urlParams.get('invoice_id');

  if (invoiceId) {
    // Poll invoice status or show success message
    checkInvoiceStatus(invoiceId);
  }
}

async function checkInvoiceStatus(invoiceId) {
  const response = await fetch(
    `http://localhost:5001/api/invoices/${invoiceId}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      }
    }
  );

  const data = await response.json();

  if (data.result.status === 'Paid') {
    showSuccessMessage('Payment successful!');
  } else {
    // Payment might still be processing
    setTimeout(() => checkInvoiceStatus(invoiceId), 3000);
  }
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `validation_error` | Invalid request data |
| `not_found` | Invoice/Payment not found |
| `unauthorized` | Missing or invalid token |
| `phonepe_error` | PhonePe API error |
| `server_error` | Internal server error |

---

## Testing

### Test PhonePe Payment (Sandbox)

1. Use UAT credentials in `.env`
2. Initiate payment
3. Use test UPI IDs:
   - Success: `success@ybl`
   - Failure: `failure@ybl`

---

## Notes for UI Developers

1. **Always handle loading states** when initiating PhonePe payments
2. **Implement retry logic** for payment status checks
3. **Show clear error messages** if payment initiation fails
4. **Don't call webhook endpoint** - it's for PhonePe servers only
5. **Use pagination** for payment lists
6. **Cache payment data** to reduce API calls
7. **Implement real-time updates** using polling or WebSockets after payment redirect

---

## Support

For backend issues: Contact backend team
For PhonePe integration: https://developer.phonepe.com/
