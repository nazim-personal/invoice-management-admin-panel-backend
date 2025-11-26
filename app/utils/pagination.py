from flask import request

def get_pagination():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
    except ValueError:
        page, per_page = 1, 10
    page = max(page, 1)
    per_page = max(min(per_page, 100), 1)
    return page, per_page
