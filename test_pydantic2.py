import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.services.fc_dispatch_service import FCDispatchRequestItem

try:
    req = FCDispatchRequestItem(
        product_id=1,
        quantity=1,
        edited_selling_price=""
    )
    print("Success")
except Exception as e:
    print("Error:", e)
