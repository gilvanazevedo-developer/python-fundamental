# logistics_dss.spec
# PyInstaller build spec for Logistics DSS
# Usage: pyinstaller packaging/logistics_dss.spec
#
# Produces:
#   dist/LogisticsDSS          (macOS / Linux single-file binary)
#   dist/LogisticsDSS.app      (macOS .app bundle)
#   dist/LogisticsDSS.exe      (Windows single-file binary)

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["../main.py"],
    pathex=[".."],
    binaries=[],
    datas=[
        # Config and locale files must be available at runtime
        ("../config/",   "config/"),
        # gettext .mo catalogs — one entry per locale/language
        ("../locale/en/LC_MESSAGES/logistics_dss.mo",    "locale/en/LC_MESSAGES/"),
        ("../locale/pt_BR/LC_MESSAGES/logistics_dss.mo", "locale/pt_BR/LC_MESSAGES/"),
        ("../locale/es/LC_MESSAGES/logistics_dss.mo",    "locale/es/LC_MESSAGES/"),
        # CustomTkinter requires its theme JSON files to be bundled explicitly
        (str(Path(sys.prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "customtkinter"),
         "customtkinter"),
    ],
    hiddenimports=[
        "customtkinter",
        "sqlalchemy.dialects.sqlite",
        "apscheduler.schedulers.background",
        "apscheduler.triggers.cron",
        "bcrypt",
        "PIL._tkinter_finder",
        "pandas",
        "numpy",
        "matplotlib",
        "matplotlib.backends.backend_tkagg",
        "openpyxl",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "matplotlib.tests", "numpy.testing"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="LogisticsDSS",
    icon="../assets/icon.ico",
    console=False,
    onefile=True,
    upx=True,
)

# macOS .app bundle (ignored on Windows/Linux)
app = BUNDLE(
    exe,
    name="LogisticsDSS.app",
    icon="../assets/icon.icns",
    bundle_identifier="com.gilvan.logistics-dss",
    info_plist={
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
    },
)
