from typing import Any, Dict, List, Optional, Type, TypeVar, Tuple
from uuid6 import uuid7
from app.database.db_manager import DBManager
from datetime import datetime, timezone
from decimal import Decimal

T = TypeVar("T", bound="BaseModel")

class BaseModel:
    _table_name: Optional[str] = None
    _allowed_fields: set[str] = set()

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize model instance, converting dates and decimals automatically.
        """
        super().__init__()
        for key, value in kwargs.items():
            if key in ('created_at', 'updated_at', 'deleted_at') and isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value)
                except (ValueError, TypeError):
                    pass
            elif key == 'price' and value is not None:
                try:
                    value = Decimal(value)
                except (ValueError, TypeError):
                    pass
            setattr(self, key, value)

    @classmethod
    def _get_base_query(cls, include_deleted: bool = False) -> str:
        return f"SELECT * FROM {cls._table_name}" + ("" if include_deleted else " WHERE deleted_at IS NULL")

    @classmethod
    def create(cls: Type[T], data: Dict[str, Any]) -> str:
        if not cls._table_name:
            raise ValueError("Model must define _table_name")
        data.setdefault("id", str(uuid7()))
        allowed: Dict[str, Any] = {k: v for k, v in data.items() if not cls._allowed_fields or k in cls._allowed_fields or k == "id"}
        allowed.setdefault("created_at", datetime.now(timezone.utc))
        columns = ", ".join(allowed.keys())
        placeholders = ", ".join(["%s"] * len(allowed))
        query = f"INSERT INTO {cls._table_name} ({columns}) VALUES ({placeholders})"
        try:
            DBManager.execute_write_query(query, tuple(allowed.values()))
            return data["id"]
        except Exception as e:
            raise ValueError(f"Failed to create record in {cls._table_name}: {e}")

    @classmethod
    def bulk_create(cls: Type[T], data_list: List[Dict[str, Any]]) -> int:
        """
        Bulk insert multiple records.
        """
        if not cls._table_name:
            raise ValueError("Model must define _table_name")
        if not data_list:
            return 0

        # Prepare data
        columns = set()
        values_list = []

        # First pass to get all columns and ensure IDs
        for data in data_list:
            data.setdefault("id", str(uuid7()))
            data.setdefault("created_at", datetime.now(timezone.utc))
            # Filter allowed fields
            filtered = {k: v for k, v in data.items() if not cls._allowed_fields or k in cls._allowed_fields or k == "id"}
            columns.update(filtered.keys())

        sorted_columns = sorted(list(columns))
        placeholders = ", ".join(["%s"] * len(sorted_columns))
        query = f"INSERT INTO {cls._table_name} ({', '.join(sorted_columns)}) VALUES ({placeholders})"

        for data in data_list:
            # Ensure all columns are present, default to None
            row_values = [data.get(col) for col in sorted_columns]
            values_list.append(tuple(row_values))

        try:
            DBManager.execute_bulk_write_query(query, values_list)
            return len(values_list)
        except Exception as e:
             raise ValueError(f"Failed to bulk create in {cls._table_name}: {e}")

    @classmethod
    def update(cls: Type[T], record_id: str, data: Dict[str, Any]) -> bool:
        if not cls._table_name:
            raise ValueError("Model must define _table_name")
        if not cls.find_by_id(record_id):
            return False
        data = {k: v for k, v in data.items() if k not in ("id", "created_at") and (not cls._allowed_fields or k in cls._allowed_fields)}
        data["updated_at"] = datetime.now(timezone.utc)
        if not data:
            return True
        set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE {cls._table_name} SET {set_clause} WHERE id = %s"
        try:
            DBManager.execute_write_query(query, tuple(list(data.values()) + [record_id]))
            return True
        except Exception as e:
            raise ValueError(f"Failed to update record in {cls._table_name}: {e}")

    @classmethod
    def find_all(cls: Type[T], include_deleted: bool = False) -> List[T]:
        results: List[Dict[str, Any]] = DBManager.execute_query(cls._get_base_query(include_deleted), fetch='all') or []
        return [cls.from_row(r) for r in results if r]

    @classmethod
    def find_by_id(cls: Type[T], id: str, include_deleted: bool = False) -> Optional[T]:
        base = cls._get_base_query(include_deleted)
        clause = "AND" if "WHERE" in base else "WHERE"
        query = f"{base} {clause} id = %s"
        result = DBManager.execute_query(query, (id,), fetch='one')
        return cls.from_row(result)

    @classmethod
    def _bulk_update(cls, ids: List[str], set_fields: Dict[str, Any], condition_deleted: Optional[bool] = None) -> int:
        if not cls._table_name or not ids:
            return 0
        placeholders = ", ".join(["%s"] * len(ids))
        set_clause = ", ".join([f"{k} = %s" for k in set_fields.keys()])
        params = list(set_fields.values()) + ids
        condition = ""
        if condition_deleted is True:
            condition = "AND deleted_at IS NULL"
        elif condition_deleted is False:
            condition = "AND deleted_at IS NOT NULL"

        count_query = f"SELECT COUNT(*) AS total FROM {cls._table_name} WHERE id IN ({placeholders}) {condition}"
        total_rows = DBManager.execute_query(count_query, tuple(ids), fetch='one') or {}
        total = int(total_rows.get("total", 0))
        if total == 0:
            return 0

        query = f"UPDATE {cls._table_name} SET {set_clause} WHERE id IN ({placeholders}) {condition}"
        DBManager.execute_write_query(query, tuple(params))
        return total

    @classmethod
    def bulk_soft_delete(cls, ids: List[str]) -> int:
        return cls._bulk_update(ids, {"deleted_at": datetime.now(timezone.utc)}, condition_deleted=True)

    @classmethod
    def bulk_restore(cls, ids: List[str]) -> int:
        return cls._bulk_update(ids, {"deleted_at": None, "updated_at": datetime.now(timezone.utc)}, condition_deleted=False)

    @classmethod
    def find_with_pagination_and_count(cls: Type[T], page: int = 1, per_page: int = 10, include_deleted: bool = False) -> Tuple[List[T], int]:
        offset = (page - 1) * per_page
        results: List[Dict[str, Any]] = DBManager.execute_query(f"{cls._get_base_query(include_deleted)} LIMIT %s OFFSET %s", (per_page, offset), fetch='all') or []
        items = [cls.from_row(r) for r in results if r]

        count_query = f"SELECT COUNT(*) AS count FROM {cls._table_name}" + ("" if include_deleted else " WHERE deleted_at IS NULL")
        total = int((DBManager.execute_query(count_query, fetch='one') or {}).get("count", 0))
        return items, total

    @classmethod
    def search(cls: Type[T], search_term: str, search_fields: List[str], include_deleted: bool = False) -> List[T]:
        base = cls._get_base_query(include_deleted)
        clause = "AND" if "WHERE" in base else "WHERE"
        search_conditions = " OR ".join([f"{f} LIKE %s" for f in search_fields])
        query = f"{base} {clause} ({search_conditions})"
        params = tuple([f"%{search_term}%" for _ in search_fields])
        results: List[Dict[str, Any]] = DBManager.execute_query(query, params, fetch='all') or []
        return [cls.from_row(r) for r in results if r]
