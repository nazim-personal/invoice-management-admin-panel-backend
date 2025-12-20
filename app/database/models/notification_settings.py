from .base_model import BaseModel
from app.database.db_manager import DBManager

class NotificationSettings(BaseModel):
    _table_name = 'notification_settings'

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self):
        return {
            'id': getattr(self, 'id', None),
            'user_id': getattr(self, 'user_id', None),
            'invoice_created': bool(getattr(self, 'invoice_created', True)),
            'payment_received': bool(getattr(self, 'payment_received', True)),
            'invoice_overdue': bool(getattr(self, 'invoice_overdue', True)),
            'created_at': getattr(self, 'created_at', None),
            'updated_at': getattr(self, 'updated_at', None)
        }

    @classmethod
    def from_row(cls, row):
        return cls(**row) if row else None

    @classmethod
    def get_user_settings(cls, user_id):
        """
        Get notification settings for a user.
        Creates default settings if none exist.
        """
        query = f"SELECT * FROM {cls._table_name} WHERE user_id = %s"
        row = DBManager.execute_query(query, (user_id,), fetch='one')

        if row:
            return cls.from_row(row)

        # Create default settings if none exist
        return cls.create_default_settings(user_id)

    @classmethod
    def create_default_settings(cls, user_id):
        """
        Create default notification settings for a user (all enabled).
        """
        from uuid6 import uuid7
        settings_id = str(uuid7())

        query = f"""
            INSERT INTO {cls._table_name}
            (id, user_id, invoice_created, payment_received, invoice_overdue)
            VALUES (%s, %s, TRUE, TRUE, TRUE)
        """
        DBManager.execute_write_query(query, (settings_id, user_id))

        return cls.get_user_settings(user_id)

    @classmethod
    def update_settings(cls, user_id, data):
        """
        Update notification settings for a user.
        """
        # Ensure settings exist
        settings = cls.get_user_settings(user_id)

        set_clauses = []
        params = []

        for key in ['invoice_created', 'payment_received', 'invoice_overdue']:
            if key in data:
                set_clauses.append(f"{key} = %s")
                params.append(bool(data[key]))

        if not set_clauses:
            return settings

        query = f"UPDATE {cls._table_name} SET {', '.join(set_clauses)} WHERE user_id = %s"
        params.append(user_id)

        DBManager.execute_write_query(query, tuple(params))

        return cls.get_user_settings(user_id)

    @classmethod
    def is_notification_enabled(cls, user_id, notification_type):
        """
        Check if a specific notification type is enabled for a user.

        Args:
            user_id: The user's ID
            notification_type: One of 'invoice_created', 'payment_received', 'invoice_overdue'

        Returns:
            Boolean indicating if notification is enabled
        """
        settings = cls.get_user_settings(user_id)
        return bool(getattr(settings, notification_type, True))
