# app/routes/dashboard.py
from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.database.models.dashboard_model import (
    get_dashboard_stats,
    get_sales_performance,
    get_latest_invoices
)
from app.utils.response import success_response
from app.utils.auth import require_admin, require_permission

dashboard_bp = Blueprint('dashboard_bp', __name__)

@dashboard_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required()
@require_permission('dashboard.view')
def dashboard_stats_route():
    """
    Get comprehensive dashboard analytics.
    Includes:
      - Revenue & customer stats
      - Sales performance (last 6 months)
      - Latest invoices (with customer info)
    Accessible only by authenticated admin users.
    """
    stats = get_dashboard_stats()
    sales = get_sales_performance()
    invoices = get_latest_invoices()

    return success_response(
        result={
            **stats,
            "sales_performance": sales,
            "invoices": invoices,
        },
        message="Dashboard data retrieved successfully."
    )
