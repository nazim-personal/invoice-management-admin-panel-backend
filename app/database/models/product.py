from typing import Any, Dict, List, Optional, Type, TypeVar, Tuple
from decimal import Decimal
from app.database.db_manager import DBManager
from app.utils.utils import generate_unique_product_code
from .base_model import BaseModel

T = TypeVar("T", bound="Product")


class Product(BaseModel):
    _table_name = "products"
    _allowed_fields = {"name", "product_code", "description", "price", "stock"}

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        stock_value = kwargs.get("stock")
        self.stock = int(stock_value) if stock_value is not None else 0

    @classmethod
    def from_row(cls: Type[T], row: Optional[Dict[str, Any]]) -> Optional[T]:
        return cls(**row) if isinstance(row, dict) else None

    @classmethod
    def create_product(cls, data: Dict[str, Any]) -> str:
        """
        Create a new product with UUIDv7, unique product_code, and normalized price.
        """
        data = dict(data)
        data["product_code"] = generate_unique_product_code(data.get("name", "Product"))

        # Normalize price
        price = data.get("price")
        if price is not None:
            try:
                data["price"] = Decimal(price).quantize(Decimal("0.00"))
            except Exception:
                data["price"] = Decimal("0.00")

        # Keep only allowed fields + id/product_code
        data = {k: v for k, v in data.items() if k in cls._allowed_fields or k in ("id", "product_code")}
        print(data)
        return super().create(data)

    @classmethod
    def update_product(cls, record_id: str, data: Dict[str, Any]) -> bool:
        """
        Update product fields safely, including optional stock change.
        Use `stock_change` key to increment/decrement stock atomically.
        """
        data = dict(data)  # copy to avoid mutation

        # Normalize price
        if "price" in data and data["price"] is not None:
            try:
                data["price"] = Decimal(data["price"]).quantize(Decimal("0.00"))
            except Exception:
                data["price"] = Decimal("0.00")

        # Handle atomic stock change
        stock_change = data.pop("stock_change", None)
        if stock_change is not None:
            query = f"""
                UPDATE {cls._table_name}
                SET stock = stock + %s, updated_at = NOW()
                WHERE id = %s AND deleted_at IS NULL
            """
            DBManager.execute_write_query(query, (int(stock_change), record_id))

        return super().update(record_id, data)

    @classmethod
    def search_product(cls: Type[T], search_term: str, include_deleted: bool = False) -> Tuple[List[T], int]:
        """
        Search products by name or product_code (case-insensitive).
        Returns (list of Product instances, total count)
        """
        base_query = cls._get_base_query(include_deleted)
        clause = "AND" if "WHERE" in base_query else "WHERE"

        like = f"%{search_term.lower()}%"
        query = f"""
            {base_query} {clause} (LOWER(name) LIKE %s OR LOWER(product_code) LIKE %s)
            ORDER BY created_at DESC
        """
        results = DBManager.execute_query(query, (like, like), fetch="all") or []

        # Filter out None values from from_row
        items: List[T] = []
        for r in results:
            if isinstance(r, dict):
                instance = cls.from_row(r)
                if instance is not None:
                    items.append(instance)

        count_query = f"SELECT COUNT(*) AS total FROM {cls._table_name} WHERE LOWER(name) LIKE %s OR LOWER(product_code) LIKE %s"
        if not include_deleted:
            count_query += " AND deleted_at IS NULL"
        total = int((DBManager.execute_query(count_query, (like, like), fetch="one") or {}).get("total", 0))

        return items, total

    @classmethod
    def bulk_restore(cls, ids: List[str]) -> int:
        return super().bulk_restore(ids)

    @classmethod
    def bulk_soft_delete(cls, ids: List[str]) -> int:
        return super().bulk_soft_delete(ids)
