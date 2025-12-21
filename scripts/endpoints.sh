#!/bin/bash

# ==============================================================================
#                 API Endpoint cURL Commands
# ==============================================================================
#
# INSTRUCTIONS:
#
# 1. Find the endpoint you want to test.
# 2. Copy the entire curl command.
# 3. Paste it into your terminal or import it into Postman.
# 4. **IMPORTANT**: Replace placeholder values (e.g., YOUR_ADMIN_TOKEN_HERE,
#    YOUR_USER_TOKEN_HERE, and ID numbers like 1, 2, 3) with actual values.
#
# ==============================================================================

BASE_URL="http://localhost:5001/api"

# -----------------
# Health Check
# -----------------
echo "### Health Check ###"
curl -X GET "$BASE_URL/health/"


# -----------------
# Auth Endpoints
# -----------------
echo "\n### Sign In as Admin (to get Admin Token) ###"
echo "# Supports: email, username, or identifier field"
curl -X POST -H "Content-Type: application/json" -d '{
  "email": "admin@example.com",
  "password": "Sknazim1818@"
}' "$BASE_URL/auth/sign-in/"


echo "\n### Refresh Access Token (Using Refresh Token) ###"
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_REFRESH_TOKEN_HERE" "$BASE_URL/auth/refresh/"


echo "\n### Get Current User Info (Using Access Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" "$BASE_URL/auth/me/"


echo "\n### Register a New User (Requires Admin Token) ###"
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
  "username": "testuser",
  "email": "test@example.com",
  "password": "password123",
  "name": "Test User"
}' "$BASE_URL/auth/register/"


echo "\n### Sign Out (Requires Any Valid Token) ###"
curl -X POST -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/auth/sign-out/"


# -----------------
# Permission Endpoints
# -----------------
echo "\n### List All Permissions (Requires Any Valid Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/permissions/"


echo "\n### Get User Permissions (Requires Admin Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/users/USER_ID_HERE/permissions/"


echo "\n### Grant Single Permission (Requires Admin Token) ###"
curl -X POST -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/users/USER_ID_HERE/permissions/customers.create/"


echo "\n### Update User Permissions - Replace All (Requires Admin Token) ###"
curl -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
  "permissions": ["customers.view", "customers.create", "products.view", "invoices.view"]
}' "$BASE_URL/users/USER_ID_HERE/permissions/"


echo "\n### Revoke Single Permission (Requires Admin Token) ###"
curl -X DELETE -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/users/USER_ID_HERE/permissions/customers.create/"


# -----------------
# Users Endpoints
# -----------------
echo "\n### Get All Users (Requires Admin Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/users/"

echo "\n### Get Current User Profile (Requires User Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/users/me/"

echo "\n### Get User by ID (Admin can get any, User can get self) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/users/1/"

echo "\n### Update Current User Profile (Requires User Token) ###"
curl -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" -d '{
    "name": "New Test User Name",
    "phone": "9876543210",
    "old_password": "password123",
    "password": "newpassword123",
    "billing_address": "456 New Billing Rd",
    "billing_city": "New City",
    "billing_state": "NC",
    "billing_pin": "54321",
    "billing_gst": "NEWGSTIN54321"
}' "$BASE_URL/users/me/"

echo "\n### Update a User by ID (Requires Admin Token) ###"
curl -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
    "name": "Updated Name by Admin",
    "role": "manager"
}' "$BASE_URL/users/1/"

echo "\n### Soft-Delete a User (Requires Admin Token) ###"
curl -X DELETE -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/users/2/"

echo "\n### Get Only Deleted Users (Requires Admin Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/users/?deleted=true"

echo "\n### Update User Profile (Requires User Token) ###"
curl -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" -d '{
    "name": "Updated Name",
    "phone": "+1234567890"
}' "$BASE_URL/users/profile/"

echo "\n### Change Password (Requires User Token) ###"
curl -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" -d '{
    "old_password": "current_password",
    "new_password": "new_password123"
}' "$BASE_URL/users/password/"

echo "\n### Get Billing Information (Requires User Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/users/billing/"

echo "\n### Update Billing Information (Requires User Token) ###"
curl -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" -d '{
    "billing_address": "123 Main St",
    "billing_city": "New York",
    "billing_state": "NY",
    "billing_pin": "10001",
    "billing_gst": "GST123456"
}' "$BASE_URL/users/billing/"

# -----------------
# Customers Endpoints
# -----------------
echo "\n### Create a New Customer (Requires Admin Token) ###"
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
    "name": "New Customer",
    "email": "customer@example.com",
    "phone": "1234567890",
    "address": "456 Customer Ave",
    "gst_number": "GSTIN67890"
}' "$BASE_URL/customers/"


echo "\n### Get All Customers (Requires User Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/customers/"


echo "\n### Get Customer by ID (Requires User Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/customers/1/"


echo "\n### Update a Customer (Requires Admin Token) ###"
curl -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
    "name": "Updated Customer Name"
}' "$BASE_URL/customers/1/"


echo "\n### Bulk Delete Customers (Requires Admin Token) ###"
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
    "ids": [1, 2]
}' "$BASE_URL/customers/bulk-delete/"

echo "\n### Get Only Deleted Customers (Requires Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/customers/?deleted=true"

echo "\n### Bulk Restore Customers (Requires Admin Token) ###"
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
    "ids": [1, 2]
}' "$BASE_URL/customers/bulk-restore/"


# -----------------
# Products Endpoints
# -----------------
echo "\n### Create a New Product (Requires Admin Token) ###"
# NOTE: The 'price' field handles decimals correctly (e.g., 24.30).
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
    "name": "Precision Screwdriver",
    "description": "A high-quality precision screwdriver for delicate tasks.",
    "price": 24.30,
    "stock": 150
}' "$BASE_URL/products/"


echo "\n### Get All Products (Requires User Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/products/"


echo "\n### Get Product by ID (Requires User Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/products/1/"


echo "\n### Update a Product (Requires Admin Token) ###"
# NOTE: The 'price' field handles decimals correctly (e.g., 25.50).
curl -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
    "price": 25.50
}' "$BASE_URL/products/1/"


echo "\n### Bulk Delete Products (Requires Admin Token) ###"
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
    "ids": [1, 2]
}' "$BASE_URL/products/bulk-delete/"

echo "\n### Get Only Deleted Products (Requires Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/products/?deleted=true"

echo "\n### Bulk Restore Products (Requires Admin Token) ###"
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
    "ids": [1, 2]
}' "$BASE_URL/products/bulk-restore/"


# -----------------
# Invoices Endpoints
# -----------------
echo "\n### Create a New Invoice (Single Comprehensive Example) ###"
# This single endpoint handles creating all invoices.
# Optional fields like discount, tax, and initial payment can be included.
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
    "customer_id": 1,
    "due_date": "2024-09-30",
    "items": [
        {"product_id": 1, "quantity": 10}
    ],
    "status": "Pending",

    "discount_amount": "5.50",
    "tax_percent": "8.20",

    "initial_payment": {
        "amount": "50.00",
        "method": "upi",
        "reference_no": "UPI-initial-payment-123"
    }
}' "$BASE_URL/invoices/"


echo "\n### Get All Invoices (Requires User Token) ###"
# NOTE: The response now includes the 'amount_paid' for each invoice.
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/invoices/"


echo "\n### Get Invoice by ID (Requires User Token) ###"
# NOTE: The response now includes the calculated 'amount_paid'.
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/invoices/1/"


echo "\n### Update an Invoice (Requires Admin Token) ###"
curl -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
    "status": "Paid"
}' "$BASE_URL/invoices/1/"


echo "\n### Pay an Invoice (Requires Admin Token) ###"
# NOTE: To test this, first 'Get Invoice by ID' to see the current 'amount_paid',
# then run this command, and then 'Get Invoice by ID' again to see the updated 'amount_paid'.
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
    "amount": "100.00",
    "method": "card",
    "reference_no": "PAY-12345"
}' "$BASE_URL/invoices/1/pay/"


echo "\n### Bulk Delete Invoices (Requires Admin Token) ###"
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
  "ids": ["INVOICE_ID_1", "INVOICE_ID_2"]
}' "$BASE_URL/invoices/bulk-delete/"


echo "\n### Generate Invoice PDF (Requires Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_TOKEN_HERE" "$BASE_URL/invoices/INVOICE_ID_HERE/pdf/" --output invoice.pdf


echo "\n### Bulk Restore Invoices (Requires Admin Token) ###"
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" -d '{
    "ids": [1, 2]
}' "$BASE_URL/invoices/bulk-restore/"

echo "\n### Get Only Deleted Invoices (Requires Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/invoices/?deleted=true"

# -----------------
# Payment Endpoints
# -----------------
echo "\n### Get All Payments (Requires Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/payments/"


echo "\n### Search Payments - General Search (Requires Token) ###"
# Search by reference_no or method
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/payments/search/?q=UPI"


echo "\n### Search Payments - By Method (Requires Token) ###"
# Filter by payment method: cash, card, upi, bank_transfer
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/payments/search/?method=upi"


echo "\n### Search Payments - By Reference Number (Requires Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/payments/search/?reference_no=PAY-12345"


echo "\n### Search Payments - By Date Range (Requires Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/payments/search/?start_date=2024-01-01&end_date=2024-12-31"


echo "\n### Search Payments - Combined Filters (Requires Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/payments/search/?method=upi&start_date=2024-01-01&end_date=2024-12-31"


echo "\n### Get Payment by ID with Customer/Invoice Details (Requires Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/payments/PAYMENT_ID_HERE/"


echo "\n### Get Payments for Invoice (Requires Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/invoices/INVOICE_ID_HERE/payments/"


# -----------------
# PhonePe Payment Gateway Endpoints
# -----------------
echo "\n### Initiate PhonePe Payment for Invoice (Requires Token) ###"
# This will return a payment URL for the customer to complete payment
curl -X POST -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/invoices/INVOICE_ID_HERE/phonepe-payment/"


echo "\n### PhonePe Webhook (Called by PhonePe - No Auth Required) ###"
# This endpoint is called automatically by PhonePe when payment status changes
# You don't need to call this manually - it's for PhonePe's servers only
# Example payload structure (for reference):
# curl -X POST -H "Content-Type: application/json" -H "X-VERIFY: signature_here" -d '{
#   "response": "base64_encoded_payment_response"
# }' "$BASE_URL/webhooks/phonepe/"

# -----------------
# Dashboard Endpoints
# -----------------
echo "\n### Get Dashboard Stats (Requires Admin Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/dashboard/stats/"


# -----------------
# Activities Endpoints
# -----------------
echo "\n### Get All Activities (Requires Admin/Manager Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/activities/"


echo "\n### Get My Activities (Requires User Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/activities/me/"


echo "\n### Get Invoice Activities (Requires User Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/invoices/INVOICE_ID_HERE/activities/"


echo "\n### Get Customer Activities (Requires User Token) ###"
curl -X GET -H "Authorization: Bearer YOUR_USER_TOKEN_HERE" "$BASE_URL/customers/CUSTOMER_ID_HERE/activities/"


# -----------------
# Reports Endpoints
# -----------------
echo "\n### Get Sales Report (Requires Report View Permission) ###"
# Query Params: start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), period (daily, weekly, monthly, yearly)
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/reports/sales/?period=monthly"


echo "\n### Get Payments Report (Requires Report View Permission) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/reports/payments/?period=monthly"


echo "\n### Get Customer Aging Report (Requires Report View Permission) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/reports/customers/aging/"


echo "\n### Get Top Products Report (Requires Report View Permission) ###"
# Query Params: limit (default 10)
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/reports/products/top/?limit=5"


echo "\n### Get Summary Stats (Requires Report View Permission) ###"
curl -X GET -H "Authorization: Bearer YOUR_ADMIN_TOKEN_HERE" "$BASE_URL/reports/summary/"
