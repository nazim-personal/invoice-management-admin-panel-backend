-- ==================================================================
--                      DATABASE SCHEMA
-- ==================================================================
-- This script defines the database schema for the application.
-- It creates all the necessary tables, columns, relationships, and indexes.
-- ==================================================================

-- Drop existing tables in reverse order of creation to handle foreign keys
DROP TABLE IF EXISTS token_blacklist;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS invoice_items;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS user_permissions;
DROP TABLE IF EXISTS users;


-- ------------------------------------------------------------------
-- Table: users
-- Purpose: Stores user accounts, credentials, and profile information.
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id CHAR(36) PRIMARY KEY,               -- UUID for unique user identification
  username VARCHAR(100) UNIQUE NOT NULL, -- User's unique login name
  email VARCHAR(255) UNIQUE NOT NULL,    -- User's unique email address
  password_hash VARCHAR(255) NOT NULL,   -- Hashed password for security
  name VARCHAR(255),                     -- User's full name
  phone VARCHAR(20),                     -- User's phone number
  role ENUM('admin','staff','manager') DEFAULT 'staff', -- User's role for access control
  twofa_secret VARCHAR(64),              -- Secret key for two-factor authentication
  billing_address TEXT,                     -- Billing address details
  billing_city VARCHAR(120),
  billing_state VARCHAR(120),
  billing_pin VARCHAR(20),
  billing_gst VARCHAR(50),                  -- User's GST number for billing
  company_name VARCHAR(255),                -- Company Name for PDF
  company_address TEXT,                     -- Company Address for PDF
  company_city VARCHAR(120),                -- Company City/State/PIN for PDF
  company_phone VARCHAR(20),                -- Company Phone for PDF
  company_email VARCHAR(255),               -- Company Email for PDF
  company_gst VARCHAR(50),                  -- Company GST for PDF
  currency_symbol VARCHAR(10) DEFAULT '₹',  -- Currency Symbol for PDF
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp of user creation
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL DEFAULT NULL,   -- Timestamp of soft deletion

  -- Indexes for faster queries
  INDEX idx_users_email (email),
  INDEX idx_users_username (username),
  INDEX idx_users_name (name),
  INDEX idx_users_role (role),
  INDEX idx_users_deleted_at (deleted_at)
);

-- ------------------------------------------------------------------
-- Table: user_permissions
-- Purpose: Stores granted permissions for each user (admin has all automatically)
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_permissions (
  id CHAR(36) PRIMARY KEY,               -- UUID for unique permission record identification
  user_id CHAR(36) NOT NULL,             -- Foreign key linking to the user
  permission VARCHAR(100) NOT NULL,      -- Permission key (e.g., 'customers.create')
  granted_by CHAR(36),                   -- User ID who granted this permission
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp of permission grant
  deleted_at TIMESTAMP NULL DEFAULT NULL,   -- Timestamp of soft deletion

  -- Foreign key constraints
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL,

  -- Ensure unique user-permission combinations
  UNIQUE KEY unique_user_permission (user_id, permission, deleted_at),

  -- Indexes for faster queries
  INDEX idx_user_permissions_user_id (user_id),
  INDEX idx_user_permissions_permission (permission),
  INDEX idx_user_permissions_deleted_at (deleted_at)
);

-- ------------------------------------------------------------------
-- Table: customers
-- Purpose: Stores information about the customers.
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
  id CHAR(36) PRIMARY KEY,               -- UUID for unique customer identification
  name VARCHAR(255) NOT NULL,              -- Customer's name
  email VARCHAR(255) UNIQUE,               -- Customer's unique email address
  phone VARCHAR(20),                       -- Customer's phone number
  address TEXT,                            -- Customer's physical address
  gst_number VARCHAR(50),                  -- Customer's GST identification number
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp of customer creation
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL DEFAULT NULL,   -- Timestamp of soft deletion

  -- Indexes for faster queries
  INDEX idx_customers_name (name),
  INDEX idx_customers_email (email),
  INDEX idx_customers_phone (phone),
  INDEX idx_customers_gst_number (gst_number),
  INDEX idx_customers_deleted_at (deleted_at)
);

-- ------------------------------------------------------------------
-- Table: products
-- Purpose: Stores details of all products or services offered.
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
  id CHAR(36) PRIMARY KEY,               -- UUID for unique product identification
  product_code VARCHAR(50) UNIQUE NOT NULL,-- Unique code for product identification
  name VARCHAR(255) NOT NULL,              -- Name of the product
  description TEXT,                        -- Detailed description of the product
  price DECIMAL(10,2) NOT NULL,            -- Price of the product
  stock INT DEFAULT 0,                     -- Current stock level
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp of product creation
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL DEFAULT NULL,   -- Timestamp of soft deletion

  -- Indexes for faster queries
  INDEX idx_products_code_name (product_code, name),
  INDEX idx_products_name (name),
  INDEX idx_products_price (price),
  INDEX idx_products_stock (stock),
  INDEX idx_products_deleted_at (deleted_at)
);

-- ------------------------------------------------------------------
-- Table: invoices
-- Purpose: Stores the main details of each invoice (header).
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoices (
  id CHAR(36) PRIMARY KEY,               -- UUID for unique invoice identification
  invoice_number VARCHAR(50) UNIQUE NOT NULL, -- Unique number for the invoice
  customer_id CHAR(36) NOT NULL,                -- Foreign key linking to the customer
  user_id CHAR(36) NOT NULL,                    -- Foreign key linking to the user who created the invoice
  due_date DATE,                           -- Date the payment is due
  subtotal_amount DECIMAL(10,2) NOT NULL,
  discount_amount DECIMAL(10,2) DEFAULT 0,
  tax_percent DECIMAL(5,2) DEFAULT 0,
  tax_amount DECIMAL(10,2) NOT NULL,
  total_amount DECIMAL(10,2) NOT NULL,     -- The final amount of the invoice
  status ENUM('Paid','Pending','Overdue', 'Partially Paid') DEFAULT 'Pending', -- Current status of the invoice
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp of invoice creation
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL DEFAULT NULL,   -- Timestamp of soft deletion

  -- Foreign key constraints
  FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,

  -- Indexes for faster queries
  INDEX idx_invoices_status_date (status),
  INDEX idx_invoices_customer_id (customer_id),
  INDEX idx_invoices_user_id (user_id),
  INDEX idx_invoices_due_date (due_date),
  INDEX idx_invoices_total_amount (total_amount),
  INDEX idx_invoices_deleted_at (deleted_at)
);

-- ------------------------------------------------------------------
-- Table: invoice_items
-- Purpose: Stores individual line items for each invoice.
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoice_items (
  id CHAR(36) PRIMARY KEY,               -- UUID for unique invoice item identification
  invoice_id CHAR(36) NOT NULL,                 -- Foreign key linking to the invoice
  product_id CHAR(36) NOT NULL,                 -- Foreign key linking to the product
  quantity INT NOT NULL,                   -- Quantity of the product sold
  price DECIMAL(10,2) NOT NULL,            -- Price per unit at the time of sale
  total DECIMAL(10,2) NOT NULL,            -- Total amount for this line item (quantity * price)
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL DEFAULT NULL,   -- Timestamp of soft deletion
  -- Foreign key constraints
  FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,

  -- Indexes for faster queries
  INDEX idx_invoice_items_invoice (invoice_id),
  INDEX idx_invoice_items_product_id (product_id),
  INDEX idx_invoice_items_deleted_at (deleted_at)
);

-- ------------------------------------------------------------------
-- Table: payments
-- Purpose: Records all payments made against invoices.
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
  id CHAR(36) PRIMARY KEY,               -- UUID for unique payment identification
  invoice_id CHAR(36) NOT NULL,                 -- Foreign key linking to the invoice being paid
  amount DECIMAL(10,2) NOT NULL,           -- The amount that was paid
  payment_date DATE NOT NULL,              -- The date the payment was made
  method ENUM('cash','card','upi','bank_transfer') DEFAULT 'cash', -- Method of payment
  reference_no VARCHAR(100),               -- A reference number from the payment processor
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp of payment record creation
  updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL DEFAULT NULL,   -- Timestamp of soft deletion
  -- Foreign key constraints
  FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,

  -- Indexes for faster queries
  INDEX idx_payments_invoice_id (invoice_id),
  INDEX idx_payments_date (payment_date),
  INDEX idx_payments_method (method),
  INDEX idx_payments_reference_no (reference_no),
  INDEX idx_payments_deleted_at (deleted_at)
);

-- ------------------------------------------------------------------
-- Table: activity_logs
-- Purpose: Stores audit logs for system activities.
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_logs (
  id CHAR(36) PRIMARY KEY,               -- UUID for unique log entry
  user_id CHAR(36) NOT NULL,             -- User who performed the action
  action VARCHAR(100) NOT NULL,          -- Action name (e.g., INVOICE_CREATED)
  entity_type VARCHAR(50) NOT NULL,      -- Entity type (e.g., invoice, customer)
  entity_id CHAR(36),                    -- ID of the affected entity
  details JSON,                          -- JSON details about the action
  ip_address VARCHAR(45),                -- IP address of the user
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp of action

  FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX idx_activity_user (user_id),
  INDEX idx_activity_entity (entity_type, entity_id),
  INDEX idx_activity_created_at (created_at)
);

-- ------------------------------------------------------------------
-- Table: token_blacklist
-- Purpose: Stores blacklisted JWT tokens to handle logouts.
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS token_blacklist (
  id CHAR(36) PRIMARY KEY,                -- Unique identifier for the blacklisted token
  user_id CHAR(36) NOT NULL,                      -- The user associated with the token
  token VARCHAR(512) NOT NULL,               -- The blacklisted JWT token
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp when the token was blacklisted
  deleted_at TIMESTAMP NULL DEFAULT NULL,   -- Timestamp of soft deletion

  -- Foreign key constraint
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,

  -- Indexes for faster queries
  INDEX idx_token_blacklist_token (token),
  INDEX idx_token_blacklist_deleted_at (deleted_at)
);
