"""
Locale completeness tests — ensure pt_BR and es catalogs are in sync with
the English master and that all binary .mo files exist.

These tests parse the .po text files directly (no gettext import needed)
so they run in any environment without compiled binaries.
"""

import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_LOCALE_DIR = PROJECT_ROOT / "locale"
_DOMAIN = "logistics_dss"


# ---------------------------------------------------------------------------
# Helper: parse a .po file into {msgid: msgstr} (skips header entry)
# ---------------------------------------------------------------------------

def _parse_po(locale: str) -> dict[str, str]:
    po_path = _LOCALE_DIR / locale / "LC_MESSAGES" / f"{_DOMAIN}.po"
    assert po_path.exists(), f".po file not found: {po_path}"
    text = po_path.read_text(encoding="utf-8")

    entries: dict[str, str] = {}
    blocks = re.split(r'\n\n+', text.strip())
    for block in blocks:
        id_m = re.search(r'^msgid\s+"((?:[^"\\]|\\.)*)"', block, re.MULTILINE)
        str_m = re.search(r'^msgstr\s+"((?:[^"\\]|\\.)*)"', block, re.MULTILINE)
        if id_m and str_m:
            msgid = id_m.group(1)
            if msgid:  # skip header
                entries[msgid] = str_m.group(1)
    return entries


def _get_en_msgids() -> set[str]:
    return set(_parse_po("en").keys())


# ---------------------------------------------------------------------------
# 1. pt_BR contains every msgid present in the English catalog
# ---------------------------------------------------------------------------

class TestPtBRHasAllEnMsgids:

    def test_no_missing_msgids(self):
        en_ids = _get_en_msgids()
        pt_entries = _parse_po("pt_BR")
        missing = en_ids - set(pt_entries.keys())
        assert not missing, f"pt_BR is missing msgids: {sorted(missing)}"


# ---------------------------------------------------------------------------
# 2. es contains every msgid present in the English catalog
# ---------------------------------------------------------------------------

class TestEsHasAllEnMsgids:

    def test_no_missing_msgids(self):
        en_ids = _get_en_msgids()
        es_entries = _parse_po("es")
        missing = en_ids - set(es_entries.keys())
        assert not missing, f"es is missing msgids: {sorted(missing)}"


# ---------------------------------------------------------------------------
# 3. pt_BR has no empty msgstr for any key that exists in English
# ---------------------------------------------------------------------------

class TestPtBRMsgstrNotEmpty:

    def test_all_msgstr_filled(self):
        en_ids = _get_en_msgids()
        pt_entries = _parse_po("pt_BR")
        empty = [k for k in en_ids if k in pt_entries and not pt_entries[k].strip()]
        assert not empty, f"pt_BR has empty msgstr for: {sorted(empty)}"


# ---------------------------------------------------------------------------
# 4. es has no empty msgstr for any key that exists in English
# ---------------------------------------------------------------------------

class TestEsMsgstrNotEmpty:

    def test_all_msgstr_filled(self):
        en_ids = _get_en_msgids()
        es_entries = _parse_po("es")
        empty = [k for k in en_ids if k in es_entries and not es_entries[k].strip()]
        assert not empty, f"es has empty msgstr for: {sorted(empty)}"


# ---------------------------------------------------------------------------
# 5. Plural-Forms header is defined in all .po files
# ---------------------------------------------------------------------------

class TestPluralFormsDefined:

    @pytest.mark.parametrize("locale", ["en", "pt_BR", "es"])
    def test_plural_forms_header_present(self, locale):
        po_path = _LOCALE_DIR / locale / "LC_MESSAGES" / f"{_DOMAIN}.po"
        text = po_path.read_text(encoding="utf-8")
        assert "Plural-Forms:" in text, f"Plural-Forms header missing in {locale}"


# ---------------------------------------------------------------------------
# 6. Compiled .mo binary exists next to each .po file
# ---------------------------------------------------------------------------

class TestMoFilesExist:

    @pytest.mark.parametrize("locale", ["en", "pt_BR", "es"])
    def test_mo_exists(self, locale):
        mo_path = _LOCALE_DIR / locale / "LC_MESSAGES" / f"{_DOMAIN}.mo"
        assert mo_path.exists(), f"Compiled .mo not found: {mo_path}"
