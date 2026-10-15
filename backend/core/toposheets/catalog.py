import csv
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent.parent
SEARCH_PATHS = [
    CURRENT_DIR / "data",
    PROJECT_ROOT / "data" / "catalog" / "toposheets",
    Path("/home/himalaya/Projects/GeoHarvest/data/catalog/toposheets"),
    Path("/home/himalaya/Projects/testscraper/checkgh/data/catalog/toposheets"),
]

_PDF_CATALOG: Optional[Dict[str, Dict[str, Any]]] = None
_TIFF_CATALOG: Optional[Dict[str, Dict[str, Any]]] = None


def normalize_sheet_key(sheet_no: str) -> str:
    """Normalize sheet number to uppercase underscore format (e.g. '40F/5' -> '40F_5')."""
    if not sheet_no:
        return ""
    cleaned = re.sub(r"\s+", "", sheet_no).upper()
    cleaned = cleaned.replace("/", "_")
    if cleaned.startswith("SOI_"):
        cleaned = cleaned[4:]
    return cleaned


def _find_catalog_file(filename: str) -> Optional[Path]:
    for base in SEARCH_PATHS:
        p = base / filename
        if p.exists() and p.stat().st_size > 0:
            return p
    return None


def _load_catalogs() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    global _PDF_CATALOG, _TIFF_CATALOG
    if _PDF_CATALOG is not None and _TIFF_CATALOG is not None:
        return _PDF_CATALOG, _TIFF_CATALOG

    pdf_map: Dict[str, Dict[str, Any]] = {}
    tiff_map: Dict[str, Dict[str, Any]] = {}

    pdf_path = _find_catalog_file("pdf_listing.csv")
    if pdf_path:
        try:
            with open(pdf_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if len(row) >= 3 and row[0] != "name":
                        name = row[0].strip()
                        size = int(row[1]) if row[1].isdigit() else 0
                        url = row[2].strip()
                        base = name.replace(".pdf", "").upper()
                        parts = base.split("-")
                        for p in parts:
                            clean_k = normalize_sheet_key(p)
                            pdf_map[clean_k] = {
                                "file_name": name,
                                "size": size,
                                "url": url,
                            }
        except Exception:
            logger.warning("Failed to load pdf_listing.csv", exc_info=True)

    tiff_path = _find_catalog_file("tiff_listing.csv")
    if tiff_path:
        try:
            with open(tiff_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if len(row) >= 3 and row[0] != "name":
                        name = row[0].strip()
                        size = int(row[1]) if row[1].isdigit() else 0
                        url = row[2].strip()
                        base = name.replace(".tif", "").upper()
                        parts = base.split("-")
                        for p in parts:
                            clean_k = normalize_sheet_key(p)
                            tiff_map[clean_k] = {
                                "file_name": name,
                                "size": size,
                                "url": url,
                            }
        except Exception:
            logger.warning("Failed to load tiff_listing.csv", exc_info=True)

    _PDF_CATALOG = pdf_map
    _TIFF_CATALOG = tiff_map
    logger.info("Loaded %d PDF release assets and %d TIFF release assets", len(pdf_map), len(tiff_map))
    return _PDF_CATALOG, _TIFF_CATALOG


def get_sheet_release_info(sheet_no: str) -> Dict[str, Any]:
    """
    Look up verified release download URLs and file sizes for a given sheet number.
    Returns:
        {
            "sheet_number": original string,
            "normalized_key": "40F_5",
            "pdf_url": str or None,
            "pdf_size": int or None,
            "georef_url": str or None,
            "georef_size": int or None,
            "has_pdf": bool,
            "has_georef": bool,
            "direct_available": bool,
        }
    """
    pdf_catalog, tiff_catalog = _load_catalogs()
    key = normalize_sheet_key(sheet_no)

    pdf_entry = pdf_catalog.get(key)
    tiff_entry = tiff_catalog.get(key)

    has_pdf = pdf_entry is not None
    has_georef = tiff_entry is not None

    return {
        "sheet_number": sheet_no,
        "normalized_key": key,
        "pdf_url": pdf_entry["url"] if pdf_entry else None,
        "pdf_size": pdf_entry["size"] if pdf_entry else None,
        "pdf_file_name": pdf_entry["file_name"] if pdf_entry else None,
        "georef_url": tiff_entry["url"] if tiff_entry else None,
        "georef_size": tiff_entry["size"] if tiff_entry else None,
        "georef_file_name": tiff_entry["file_name"] if tiff_entry else None,
        "has_pdf": has_pdf,
        "has_georef": has_georef,
        "direct_available": has_pdf or has_georef,
    }
