"""
Logistics DSS Configuration Settings
Centralized configuration for the inventory management system.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = DATA_DIR / "database"
IMPORTS_DIR = DATA_DIR / "imports"
EXPORTS_DIR = DATA_DIR / "exports"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
for dir_path in [DATABASE_DIR, IMPORTS_DIR, EXPORTS_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Database Configuration
DATABASE_NAME = os.getenv("DATABASE_NAME", "logistics_dss.db")
DATABASE_PATH = DATABASE_DIR / DATABASE_NAME

# SQLite Configuration
SQLITE_TIMEOUT = 30  # seconds
SQLITE_CHECK_SAME_THREAD = False

# Import Configuration
SUPPORTED_EXTENSIONS = [".csv", ".xlsx", ".xls"]
MAX_FILE_SIZE_MB = 50
BATCH_SIZE = 1000  # Records per batch for bulk operations

# Validation Configuration
STRICT_VALIDATION = os.getenv("STRICT_VALIDATION", "true").lower() == "true"
LOG_VALIDATION_ERRORS = True
MAX_VALIDATION_ERRORS = 100  # Stop validation after this many errors

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE_MAX_SIZE = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

# UI Configuration (Phase 2)
WINDOW_TITLE = "Logistics DSS"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 600
APPEARANCE_MODE = os.getenv("APPEARANCE_MODE", "dark")
COLOR_THEME = "blue"
AUTO_REFRESH_SECONDS = 0  # 0 = disabled
NAV_WIDTH = 180

# Internationalisation
DEFAULT_LANGUAGE = "en"  # supported: "en", "pt", "es"
