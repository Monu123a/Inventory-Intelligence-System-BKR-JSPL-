import re

with open("app/main.py", "r") as f:
    content = f.read()

# Add imports
import_str = "from app.api.dependencies import get_current_user\nfrom fastapi import Depends, APIRouter\nfrom app.models.schema import User\n\n"
content = import_str + content

# Create router
router_str = "\n\nlegacy_router = APIRouter(prefix=\"/api\", dependencies=[Depends(get_current_user)])\n\n"
content = content.replace("# Endpoints\n# ---------------------------------------------------------------------------", "# Endpoints\n# ---------------------------------------------------------------------------" + router_str)

# Replace @app. decorators
content = re.sub(r'@app\.(post|get|delete|put)\("/api/([^"]+)"\)', r'@legacy_router.\1("/\2")', content)

# Include the router at the bottom
content = content.replace('app.include_router(company_settings_router, prefix="/api")', 'app.include_router(company_settings_router, prefix="/api")\napp.include_router(legacy_router)')

# Sanitize upload path
content = content.replace('dest = os.path.join(UPLOAD_DIR, f.filename)', 'dest = os.path.join(UPLOAD_DIR, os.path.basename(f.filename))')

with open("app/main.py", "w") as f:
    f.write(content)
