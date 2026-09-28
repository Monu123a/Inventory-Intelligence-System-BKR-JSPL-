import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.api.routers.pos import PosCheckoutRequest

try:
    req = PosCheckoutRequest(
        items=[],
        custom_invoice_date=""
    )
    print("Success")
except Exception as e:
    print("Error:", e)
