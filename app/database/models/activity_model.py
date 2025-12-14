
from .base_model import BaseModel
from app.database.db_manager import DBManager
import json

class ActivityLog(BaseModel):
    _table_name = 'activity_logs'

    def __init__(self, id, user_id, action, entity_type, entity_id=None, details=None, ip_address=None, created_at=None, **kwargs):
        self.id = id
        self.user_id = user_id
        self.action = action
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.details = details if isinstance(details, dict) else (json.loads(details) if details else {})
        self.ip_address = ip_address
        self.created_at = created_at

        # Absorb extra
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def create_log(cls, user_id, action, entity_type, entity_id=None, details=None, ip_address=None):
        from uuid6 import uuid7
        log_id = str(uuid7())

        details_json = json.dumps(details, default=str) if details else None

        query = f"""
            INSERT INTO {cls._table_name}
            (id, user_id, action, entity_type, entity_id, details, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        DBManager.execute_write_query(query, (log_id, user_id, action, entity_type, entity_id, details_json, ip_address))
        return log_id

    @classmethod
    def list_logs(cls, user_id=None, entity_type=None, entity_id=None, limit=50, offset=0):
        where = []
        params = []

        if user_id:
            where.append("user_id = %s")
            params.append(user_id)

        if entity_type:
            where.append("entity_type = %s")
            params.append(entity_type)

        if entity_id:
            where.append("entity_id = %s")
            params.append(entity_id)

        where_sql = " WHERE " + " AND ".join(where) if where else ""

        query = f"""
            SELECT a.*, u.username as user_name
            FROM {cls._table_name} a
            JOIN users u ON a.user_id = u.id
            {where_sql}
            ORDER BY a.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        rows = DBManager.execute_query(query, tuple(params), fetch='all')

        logs = []
        if rows:
            for row in rows:
                log = cls(**row)
                # Attach username if available (not part of model init but useful for display)
                log.user_name = row.get('user_name')
                logs.append(log)

        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM {cls._table_name} {where_sql}"
        count_result = DBManager.execute_query(count_query, tuple(params[:-2]), fetch='one')
        total = count_result['total'] if count_result else 0

        return logs, total
