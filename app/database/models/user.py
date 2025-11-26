
from werkzeug.security import generate_password_hash, check_password_hash
from .base_model import BaseModel
from app.database.db_manager import DBManager

class User(BaseModel):
    _table_name = 'users'

    def __init__(self, id, username, email, password_hash, role='staff', name=None, phone=None, billing_address=None, billing_city=None, billing_state=None, billing_pin=None, billing_gst=None, **kwargs):
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
            'billing_gst': self.billing_gst
        }

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        # Unpack the row dictionary into the constructor
        return cls(**row)

    @classmethod
    def create(cls, data):
        hashed_password = generate_password_hash(data['password'], method='scrypt')
        role = data.get('role', 'staff')
        name = data.get('name')
        phone = data.get('phone')
        username = data['username']
        email = data['email']

        query = f'INSERT INTO {cls._table_name} (username, email, password_hash, name, role, phone) VALUES (%s, %s, %s, %s, %s, %s)'
        user_id = DBManager.execute_write_query(query, (username, email, hashed_password, name, role, phone))
        
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
