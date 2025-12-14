-- Migration: Add PhonePe Payment Gateway fields to payments table
-- Date: 2025-12-14

ALTER TABLE payments
ADD COLUMN transaction_id VARCHAR(255) DEFAULT NULL COMMENT 'PhonePe transaction ID',
ADD COLUMN payment_gateway VARCHAR(50) DEFAULT NULL COMMENT 'Payment gateway name (e.g., phonepe)',
ADD COLUMN gateway_response TEXT DEFAULT NULL COMMENT 'Raw gateway response JSON';

-- Add index for faster transaction_id lookups
CREATE INDEX idx_payments_transaction_id ON payments(transaction_id);
CREATE INDEX idx_payments_gateway ON payments(payment_gateway);
