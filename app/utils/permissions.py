# Permission Constants
# Defines all available permissions in the system

PERMISSIONS = {
    # Customer permissions
    'customers.view': 'View customers list and details',
    'customers.create': 'Create new customers',
    'customers.update': 'Update customer information',
    'customers.delete': 'Soft delete customers',
    'customers.restore': 'Restore deleted customers',

    # Product permissions
    'products.view': 'View products list and details',
    'products.create': 'Create new products',
    'products.update': 'Update product information',
    'products.delete': 'Soft delete products',
    'products.restore': 'Restore deleted products',

    # Invoice permissions
    'invoices.view': 'View invoices list and details',
    'invoices.create': 'Create new invoices',
    'invoices.update': 'Update invoice information',
    'invoices.delete': 'Soft delete invoices',
    'invoices.restore': 'Restore deleted invoices',

    # Payment permissions
    'payments.view': 'View payment records',
    'payments.create': 'Record new payments',

    # User management permissions
    'users.view': 'View users list and details',
    'users.create': 'Create new users',
    'users.update': 'Update user information',
    'users.delete': 'Soft delete users',
    'users.permissions': 'Manage user permissions',

    # Dashboard permissions
    'dashboard.view': 'View dashboard statistics and analytics',
}

# Permission categories for UI grouping
PERMISSION_CATEGORIES = {
    'Customers': ['customers.view', 'customers.create', 'customers.update', 'customers.delete', 'customers.restore'],
    'Products': ['products.view', 'products.create', 'products.update', 'products.delete', 'products.restore'],
    'Invoices': ['invoices.view', 'invoices.create', 'invoices.update', 'invoices.delete', 'invoices.restore'],
    'Payments': ['payments.view', 'payments.create'],
    'Users': ['users.view', 'users.create', 'users.update', 'users.delete', 'users.permissions'],
    'Dashboard': ['dashboard.view'],
}
