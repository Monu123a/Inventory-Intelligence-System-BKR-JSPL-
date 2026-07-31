import os
import sys

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from app.models.db import engine, Base
from app.models.schema import *  # Import all schemas so Base knows about them

print("Applying schema changes...")
Base.metadata.create_all(bind=engine)
print("Schema updated successfully.")
