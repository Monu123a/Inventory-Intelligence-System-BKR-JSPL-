import sys
with open('backend/app/api/routers/auth.py', 'r') as f:
    content = f.read()

new_logic = """def verify_admin_action_password(input_password: Optional[str], current_user: User):
    if not input_password or not input_password.strip():
        raise HTTPException(status_code=400, detail="Admin password required")

    if input_password.strip() == "REQUEST_APPROVAL":
        raise HTTPException(status_code=403, detail="Admin access required")
"""

content = content.replace('def verify_admin_action_password(input_password: Optional[str], current_user: User):\n    if not input_password or not input_password.strip():\n        raise HTTPException(status_code=400, detail="Admin password required")', new_logic)

with open('backend/app/api/routers/auth.py', 'w') as f:
    f.write(content)
