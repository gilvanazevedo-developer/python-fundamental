#!/usr/bin/env python3
"""
tools/extract_strings.py
------------------------
Scan all Python source files for gettext-style translate() / _() calls and
compare against the English .po catalog to identify:

  1. Strings in source that are MISSING from the .po file (need to be added).
  2. Entries in the .po file that are NOT referenced in source (orphaned / stale).
  3. Translation completeness for every non-English locale.

Usage::

    python tools/extract_strings.py [--src SRC_DIR] [--locale LOCALE_DIR]

Example output::

    === Source scan complete ===
    Found 142 unique msgids in source.

    === Checking en catalog ===
    Missing from .po: 0 strings
    Orphaned in .po:  2 strings

    === Checking pt_BR catalog ===
    Completeness: 142 / 142 (100.0 %)

    === Checking es catalog ===
    Completeness: 141 / 142 (99.3 %)
    Untranslated: "Forecasting"
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent
_DEFAULT_SRC = _REPO_ROOT / "src"
_DEFAULT_LOCALE = _REPO_ROOT / "locale"
_DOMAIN = "logistics_dss"
_SUPPORTED_LOCALES = ("en", "pt_BR", "es")

# Regex to extract msgid / msgstr from .po files (handles quoted strings only)
_MSGID_RE = re.compile(r'^msgid\s+"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)
_MSGSTR_RE = re.compile(r'^msgstr\s+"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)


# ---------------------------------------------------------------------------
# Source scanner
# ---------------------------------------------------------------------------

def scan_source(src_dir: Path) -> set[str]:
    """Walk *src_dir* and extract all string literals passed to translate() or _()."""
    found: set[str] = set()
    pattern = re.compile(
        r'(?:translate|_gt|_)\(\s*["\']([^"\']+)["\']\s*\)',
    )
    for py_file in src_dir.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in pattern.finditer(text):
            found.add(m.group(1))
    return found


# ---------------------------------------------------------------------------
# .po parser
# ---------------------------------------------------------------------------

def parse_po(po_path: Path) -> dict[str, str]:
    """Return {msgid: msgstr} for every non-header entry in the .po file."""
    if not po_path.exists():
        return {}
    text = po_path.read_text(encoding="utf-8")
    entries: dict[str, str] = {}
    # Split on blank lines to get individual blocks
    blocks = re.split(r'\n\n+', text.strip())
    for block in blocks:
        id_m = re.search(r'^msgid\s+"((?:[^"\\]|\\.)*)"', block, re.MULTILINE)
        str_m = re.search(r'^msgstr\s+"((?:[^"\\]|\\.)*)"', block, re.MULTILINE)
        if id_m and str_m:
            msgid = id_m.group(1)
            if msgid:  # skip header entry
                entries[msgid] = str_m.group(1)
    return entries


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

def _check_source_vs_catalog(source_ids: set[str], catalog: dict[str, str]) -> None:
    missing = sorted(source_ids - set(catalog))
    orphaned = sorted(set(catalog) - source_ids)
    if missing:
        print(f"  Missing from .po ({len(missing)}):")
        for m in missing:
            print(f"    - {m!r}")
    else:
        print(f"  Missing from .po: 0")
    if orphaned:
        print(f"  Orphaned in .po ({len(orphaned)}):")
        for o in orphaned:
            print(f"    - {o!r}")
    else:
        print(f"  Orphaned in .po: 0")


def _check_completeness(locale: str, en_catalog: dict[str, str], tgt_catalog: dict[str, str]) -> None:
    total = len(en_catalog)
    translated = sum(1 for k, v in tgt_catalog.items() if k in en_catalog and v)
    pct = (translated / total * 100) if total else 100.0
    print(f"  Completeness: {translated} / {total} ({pct:.1f} %)")
    untranslated = [k for k in en_catalog if not tgt_catalog.get(k)]
    if untranslated:
        print(f"  Untranslated ({len(untranslated)}):")
        for u in sorted(untranslated):
            print(f"    - {u!r}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Check .po catalog coverage")
    parser.add_argument("--src",    default=str(_DEFAULT_SRC),    help="Source directory to scan")
    parser.add_argument("--locale", default=str(_DEFAULT_LOCALE), help="Locale directory")
    args = parser.parse_args()

    src_dir = Path(args.src)
    locale_dir = Path(args.locale)

    print("=== Source scan ===")
    source_ids = scan_source(src_dir)
    print(f"Found {len(source_ids)} unique msgids in source.\n")

    en_po = locale_dir / "en" / "LC_MESSAGES" / f"{_DOMAIN}.po"
    en_catalog = parse_po(en_po)
    print(f"=== Checking en catalog ({len(en_catalog)} entries) ===")
    _check_source_vs_catalog(source_ids, en_catalog)
    print()

    for locale in _SUPPORTED_LOCALES:
        if locale == "en":
            continue
        po_path = locale_dir / locale / "LC_MESSAGES" / f"{_DOMAIN}.po"
        tgt_catalog = parse_po(po_path)
        print(f"=== Checking {locale} catalog ({len(tgt_catalog)} entries) ===")
        _check_completeness(locale, en_catalog, tgt_catalog)
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
