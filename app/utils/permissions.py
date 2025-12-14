# Permission Constants
# Defines all available permissions in the system

PERMISSIONS = {
    # Customer permissions
    'customers.list': 'View customers list',
    'customers.view': 'View customer details',
    'customers.create': 'Create new customers',
    'customers.update': 'Update customer information',
    'customers.delete': 'Soft delete customers',
    'customers.restore': 'Restore deleted customers',

    # Product permissions
    'products.list': 'View products list',
    'products.view': 'View product details',
    'products.create': 'Create new products',
    'products.update': 'Update product information',
    'products.delete': 'Soft delete products',
    'products.restore': 'Restore deleted products',

    # Invoice permissions
    'invoices.list': 'View invoices list',
    'invoices.view': 'View invoice details',
    'invoices.create': 'Create new invoices',
    'invoices.update': 'Update invoice information',
    'invoices.delete': 'Soft delete invoices',
    'invoices.restore': 'Restore deleted invoices',

    # Payment permissions
    'payments.list': 'View payment records list',
    'payments.view': 'View payment details',
    'payments.create': 'Record new payments',

    # User management permissions
    'users.list': 'View users list',
    'users.view': 'View user details',
    'users.create': 'Create new users',
    'users.update': 'Update user information',
    'users.delete': 'Soft delete users',
    'users.permissions': 'Manage user permissions',

    # Dashboard permissions
    'dashboard.view': 'View dashboard statistics and analytics',

    # Report permissions
    'reports.view': 'View system reports',
}

# Permission categories for UI grouping
PERMISSION_CATEGORIES = {
    'Customers': ['customers.list', 'customers.view', 'customers.create', 'customers.update', 'customers.delete', 'customers.restore'],
    'Products': ['products.list', 'products.view', 'products.create', 'products.update', 'products.delete', 'products.restore'],
    'Invoices': ['invoices.list', 'invoices.view', 'invoices.create', 'invoices.update', 'invoices.delete', 'invoices.restore'],
    'Payments': ['payments.list', 'payments.view', 'payments.create'],
    'Users': ['users.list', 'users.view', 'users.create', 'users.update', 'users.delete', 'users.permissions'],
    'Dashboard': ['dashboard.view'],
    'Reports': ['reports.view'],
}
