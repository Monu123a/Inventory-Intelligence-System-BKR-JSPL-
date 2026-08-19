with open("backend/app/main.py", "r") as f:
    content = f.read()

cors_patch = """
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import logging
    logger = logging.getLogger("fastapi")
    logger.error(f"Global Exception: {exc}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": traceback.format_exc()},
        headers={"Access-Control-Allow-Origin": "*"}
    )
"""

if "@app.exception_handler(Exception)" not in content:
    content = content.replace('app = FastAPI(title="Inventory Intelligence System")', 'app = FastAPI(title="Inventory Intelligence System")\n' + cors_patch)
    with open("backend/app/main.py", "w") as f:
        f.write(content)
        print("Patched main.py")
else:
    print("Already patched")
