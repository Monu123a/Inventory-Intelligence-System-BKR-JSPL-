with open('backend/app/api/routers/admin_approvals.py', 'r') as f:
    content = f.read()

verify_route = """
class VerifyPasswordPayload(BaseModel):
    password: str

@router.post("/verify-password")
def verify_dashboard_password(
    data: VerifyPasswordPayload,
    current_user: User = Depends(get_current_user)
):
    from app.api.routers.auth import verify_admin_action_password
    verify_admin_action_password(data.password, current_user)
    return {"status": "ok"}
"""

if "def verify_dashboard_password" not in content:
    content += verify_route

with open('backend/app/api/routers/admin_approvals.py', 'w') as f:
    f.write(content)
