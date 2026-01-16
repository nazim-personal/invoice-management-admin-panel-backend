
from werkzeug.security import generate_password_hash, check_password_hash
from .base_model import BaseModel
from app.database.db_manager import DBManager

class User(BaseModel):
    _table_name = 'users'

    def __init__(self, id, username, email, password_hash, role='staff', name=None, phone=None, billing_address=None, billing_city=None, billing_state=None, billing_pin=None, billing_gst=None, company_name=None, company_address=None, company_city=None, company_phone=None, company_email=None, company_gst=None, currency_symbol='₹', permissions=None, **kwargs):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.name = name
        self.phone = phone
        self.billing_address = billing_address
        self.billing_city = billing_city
        self.billing_state = billing_state
        self.billing_pin = billing_pin
        self.billing_gst = billing_gst
        self.company_name = company_name
        self.company_address = company_address
        self.company_city = company_city
        self.company_phone = company_phone
        self.company_email = company_email
        self.company_gst = company_gst
        self.currency_symbol = currency_symbol
        self.permissions = permissions
        # Absorb any extra columns that might be in the database row
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'name': self.name,
            'phone': self.phone,
            'billing_address': self.billing_address,
            'billing_city': self.billing_city,
            'billing_state': self.billing_state,
            'billing_pin': self.billing_pin,
            'billing_gst': self.billing_gst,
            'company_name': self.company_name,
            'company_address': self.company_address,
            'company_city': self.company_city,
            'company_phone': self.company_phone,
            'company_email': self.company_email,
            'company_gst': self.company_gst,
            'currency_symbol': self.currency_symbol,
            'permissions': self.get_permissions()
        }

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        # Unpack the row dictionary into the constructor
        return cls(**row)

    @classmethod
    def create(cls, data):
        from uuid6 import uuid7
        user_id = str(uuid7())
        hashed_password = generate_password_hash(data['password'], method='scrypt')
        role = data.get('role', 'staff')
        name = data.get('name')
        phone = data.get('phone')
        username = data['username']
        email = data['email']

        # Company Details
        company_name = data.get('company_name')
        company_address = data.get('company_address')
        company_city = data.get('company_city')
        company_phone = data.get('company_phone')
        company_email = data.get('company_email')
        company_gst = data.get('company_gst')
        currency_symbol = data.get('currency_symbol', '₹')
        permissions = data.get('permissions')
        if not permissions:
            from app.utils.permissions import DEFAULT_ROLE_PERMISSIONS
            permissions = DEFAULT_ROLE_PERMISSIONS.get(role, [])

        import json
        permissions_json = json.dumps(permissions) if permissions else None

        query = f'''
            INSERT INTO {cls._table_name}
            (id, username, email, password_hash, name, role, phone,
             company_name, company_address, company_city, company_phone, company_email, company_gst, currency_symbol, permissions)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        DBManager.execute_write_query(query, (
            user_id, username, email, hashed_password, name, role, phone,
            company_name, company_address, company_city, company_phone, company_email, company_gst, currency_symbol, permissions_json
        ))

        # Return the ID directly. The route will be responsible for fetching.
        return user_id

    @classmethod
    def find_by_email(cls, email, include_deleted=False):
        return cls.find_by_username_or_email(login_identifier=email, include_deleted=include_deleted)

    @classmethod
    def find_by_username(cls, username, include_deleted=False):
        return cls.find_by_username_or_email(login_identifier=username, include_deleted=include_deleted)

    @classmethod
    def find_by_username_or_email(cls, login_identifier, include_deleted=False):
        base_query = cls._get_base_query(include_deleted)
        # Use "AND" if the base query already has a "WHERE" clause (i.e., when not including deleted)
        # and "WHERE" if it doesn't.
        clause = "AND" if not include_deleted else "WHERE"
        query = f'{base_query} {clause} (username = %s OR email = %s)'
        result = DBManager.execute_query(query, (login_identifier, login_identifier), fetch='one')
        return cls.from_row(result)

    def get_permissions(self):
        """
        Get all permissions for this user.
        Admin role automatically has all permissions.
        """
        if self.role == 'admin':
            from app.utils.permissions import PERMISSIONS
            return list(PERMISSIONS.keys())

        if self.permissions:
            import json
            if isinstance(self.permissions, str):
                try:
                    return json.loads(self.permissions)
                except Exception:
                    return []
            elif isinstance(self.permissions, list):
                return self.permissions

        from app.database.models.permission_model import UserPermission
        return UserPermission.get_user_permissions(str(self.id))

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        return permission in self.get_permissions()

    @classmethod
    def has_created_entities(cls, user_id: str) -> bool:
        """
        Check if the user has created any invoices, customers, or products.
        Customers and products are checked via activity logs.
        """
        # Check invoices (direct link)
        invoice_query = "SELECT COUNT(*) as count FROM invoices WHERE user_id = %s"
        invoice_result = DBManager.execute_query(invoice_query, (user_id,), fetch='one')
        if invoice_result and invoice_result['count'] > 0:
            return True

        # Check activity logs for customer/product creation
        activity_query = """
            SELECT COUNT(*) as count FROM activity_logs
            WHERE user_id = %s AND action IN ('CUSTOMER_CREATED', 'PRODUCT_CREATED')
        """
        activity_result = DBManager.execute_query(activity_query, (user_id,), fetch='one')
        if activity_result and activity_result['count'] > 0:
            return True

        return False

    @classmethod
    def get_users_with_entities(cls, ids: List[str]) -> List[str]:
        """
        Check which users from the given list have created any invoices, customers, or products.
        Returns a list of usernames for users who cannot be deleted.
        """
        if not ids:
            return []

        placeholders = ", ".join(["%s"] * len(ids))

        # Check invoices and activity logs
        query = f"""
            SELECT DISTINCT u.username
            FROM {cls._table_name} u
            LEFT JOIN invoices i ON u.id = i.user_id
            LEFT JOIN activity_logs al ON u.id = al.user_id AND al.action IN ('CUSTOMER_CREATED', 'PRODUCT_CREATED')
            WHERE u.id IN ({placeholders}) AND u.deleted_at IS NULL
            AND (i.id IS NOT NULL OR al.id IS NOT NULL)
        """
        rows = DBManager.execute_query(query, tuple(ids), fetch='all')
        return [row['username'] for row in rows] if rows else []
