from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.database.models.report_model import ReportModel
from app.utils.response import success_response, error_response
from app.utils.auth import require_permission

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports/sales/', methods=['GET'])
@jwt_required()
@require_permission('reports.view')
def get_sales_report():
    """
    Get sales report.
    Query Params: start_date, end_date, period (daily, weekly, monthly, yearly)
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period = request.args.get('period', 'monthly')

        data = ReportModel.get_sales_report(start_date, end_date, period)
        return success_response(result=data)
    except Exception as e:
        return error_response('server_error', 'Failed to fetch sales report.', str(e), 500)

@reports_bp.route('/reports/payments/', methods=['GET'])
@jwt_required()
@require_permission('reports.view')
def get_payment_report():
    """
    Get payments report.
    Query Params: start_date, end_date, period
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        period = request.args.get('period', 'monthly')

        data = ReportModel.get_payment_report(start_date, end_date, period)
        return success_response(result=data)
    except Exception as e:
        return error_response('server_error', 'Failed to fetch payment report.', str(e), 500)

@reports_bp.route('/reports/customers/aging/', methods=['GET'])
@jwt_required()
@require_permission('reports.view')
def get_customer_aging_report():
    """
    Get customer aging report (outstanding balances).
    """
    try:
        data = ReportModel.get_customer_aging_report()
        return success_response(result=data)
    except Exception as e:
        return error_response('server_error', 'Failed to fetch customer aging report.', str(e), 500)

@reports_bp.route('/reports/products/top/', methods=['GET'])
@jwt_required()
@require_permission('reports.view')
def get_top_products_report():
    """
    Get top selling products.
    Query Params: start_date, end_date, limit
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 10))

        data = ReportModel.get_top_products_report(start_date, end_date, limit)
        return success_response(result=data)
    except Exception as e:
        return error_response('server_error', 'Failed to fetch top products report.', str(e), 500)

@reports_bp.route('/reports/summary/', methods=['GET'])
@jwt_required()
@require_permission('reports.view')
def get_summary_stats():
    """
    Get high-level summary statistics.
    """
    try:
        data = ReportModel.get_summary_stats()
        return success_response(result=data)
    except Exception as e:
        return error_response('server_error', 'Failed to fetch summary stats.', str(e), 500)
