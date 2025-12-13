import sys
import json
from decimal import Decimal
from datetime import date, datetime
from app.database.models.dashboard_model import get_dashboard_stats, get_sales_performance, get_latest_invoices

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError ("Type %s not serializable" % type(obj))

print("--- Testing get_dashboard_stats ---")
try:
    stats = get_dashboard_stats()
    print("Stats keys:", stats.keys())
    # Check for Decimals
    for k, v in stats.items():
        print(f"{k}: {type(v)} = {v}")
        if isinstance(v, Decimal):
            print(f"⚠️ {k} is Decimal!")
except Exception as e:
    print(f"❌ get_dashboard_stats failed: {e}")
    import traceback
    traceback.print_exc()

print("\n--- Testing get_sales_performance ---")
try:
    sales = get_sales_performance()
    print(f"Sales count: {len(sales)}")
    if sales:
        print("First item:", sales[0])
        for k, v in sales[0].items():
             if isinstance(v, Decimal):
                print(f"⚠️ {k} is Decimal!")
except Exception as e:
    print(f"❌ get_sales_performance failed: {e}")
    import traceback
    traceback.print_exc()

print("\n--- Testing get_latest_invoices ---")
try:
    invoices = get_latest_invoices()
    print(f"Invoices count: {len(invoices)}")
    if invoices:
        print("First invoice:", invoices[0])
        for k, v in invoices[0].items():
             if isinstance(v, Decimal):
                print(f"⚠️ {k} is Decimal!")
except Exception as e:
    print(f"❌ get_latest_invoices failed: {e}")
    import traceback
    traceback.print_exc()

print("\n--- Testing JSON Serialization (Simulation) ---")
try:
    data = {
        **stats,
        "sales_performance": sales,
        "invoices": invoices
    }
    # Flask's jsonify uses simplejson or json, which fails on Decimal unless default is set
    json.dumps(data)
    print("✅ JSON serialization successful (Standard JSON)")
except TypeError as e:
    print(f"❌ JSON serialization failed: {e}")
