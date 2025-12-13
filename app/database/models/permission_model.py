from .base_model import BaseModel
from app.database.db_manager import DBManager
from typing import List, Optional

class UserPermission(BaseModel):
    _table_name = 'user_permissions'

    @classmethod
    def from_row(cls, row):
        """Create instance from database row"""
        return cls(**row) if row else None

    @classmethod
    def grant_permission(cls, user_id: str, permission: str, granted_by: str) -> str:
        """Grant a permission to a user"""
        from app.utils.permissions import PERMISSIONS

        if permission not in PERMISSIONS:
            raise ValueError(f"Invalid permission: {permission}")

        return cls.create({
            'user_id': user_id,
            'permission': permission,
            'granted_by': granted_by
        })

    @classmethod
    def revoke_permission(cls, user_id: str, permission: str) -> bool:
        """Revoke a permission from a user (soft delete)"""
        query = f"""
            UPDATE {cls._table_name}
            SET deleted_at = NOW()
            WHERE user_id = %s AND permission = %s AND deleted_at IS NULL
        """
        DBManager.execute_write_query(query, (user_id, permission))
        return True

    @classmethod
    def get_user_permissions(cls, user_id: str) -> List[str]:
        """Get all active permissions for a user"""
        query = f"""
            SELECT permission
            FROM {cls._table_name}
            WHERE user_id = %s AND deleted_at IS NULL
        """
        rows = DBManager.execute_query(query, (user_id,), fetch='all')
        return [row['permission'] for row in rows] if rows else []

    @classmethod
    def bulk_grant_permissions(cls, user_id: str, permissions: List[str], granted_by: str) -> int:
        """Grant multiple permissions to a user"""
        count = 0
        for permission in permissions:
            try:
                cls.grant_permission(user_id, permission, granted_by)
                count += 1
            except Exception:
                # Skip duplicates or invalid permissions
                continue
        return count

    @classmethod
    def sync_permissions(cls, user_id: str, permissions: List[str], granted_by: str) -> int:
        """
        Replace all user permissions with new set.
        Soft deletes existing permissions and grants new ones.
        """
        # Soft delete all existing permissions
        query = f"""
            UPDATE {cls._table_name}
            SET deleted_at = NOW()
            WHERE user_id = %s AND deleted_at IS NULL
        """
        DBManager.execute_write_query(query, (user_id,))

        # Grant new permissions
        return cls.bulk_grant_permissions(user_id, permissions, granted_by)

    @classmethod
    def get_users_with_permission(cls, permission: str) -> List[str]:
        """Get all user IDs that have a specific permission"""
        query = f"""
            SELECT DISTINCT user_id
            FROM {cls._table_name}
            WHERE permission = %s AND deleted_at IS NULL
        """
        rows = DBManager.execute_query(query, (permission,), fetch='all')
        return [row['user_id'] for row in rows] if rows else []
