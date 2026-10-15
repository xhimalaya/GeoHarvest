"""Survey of India (SOI) Map Grid Generator.

Implements the official hierarchical indexing system for India and Adjacent Countries (IAC):
- 1:1,000,000 Million Sheets (4° lat x 4° lon)
- 1:250,000 Degree Sheets (1° lat x 1° lon, lettered A-P column-wise)
- 1:50,000 Topo Sheets (15' x 15', numbered 1-16 column-wise)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Mapping of Million Sheets covering India and neighboring Himalayan cryosphere
MILLION_SHEETS: Dict[str, Tuple[float, float, float, float]] = {
    # Northern Himalayas & Cryosphere (Ladakh, J&K, Himachal, Uttarakhand)
    "42": (72.0, 36.0, 76.0, 40.0),
    "43": (72.0, 32.0, 76.0, 36.0),  # J&K West / Kashmir Valley
    "51": (76.0, 36.0, 80.0, 40.0),  # Karakoram North
    "52": (76.0, 32.0, 80.0, 36.0),  # Ladakh Cryosphere (Leh, Hemis, Zanskar) & Himachal
    "53": (76.0, 28.0, 80.0, 32.0),  # Delhi, Uttarakhand, UP West
    "62": (80.0, 28.0, 84.0, 32.0),  # Uttarakhand East / West Nepal
    # Northern Plains & Rajasthan
    "44": (72.0, 28.0, 76.0, 32.0),  # Punjab, Haryana, North Rajasthan
    "45": (72.0, 24.0, 76.0, 28.0),  # Rajasthan Central / Aravallis
    "54": (76.0, 24.0, 80.0, 28.0),  # Madhya Pradesh North, UP Central
    "63": (80.0, 24.0, 84.0, 28.0),  # UP East, Bihar West
    "72": (84.0, 24.0, 88.0, 28.0),  # Bihar East, North Bengal, Sikkim
    # Western & Central India
    "46": (72.0, 20.0, 76.0, 24.0),  # Gujarat, Maharashtra NW
    "47": (72.0, 16.0, 76.0, 20.0),  # Maharashtra West, Goa
    "55": (76.0, 20.0, 80.0, 24.0),  # Maharashtra East, MP South
    "56": (76.0, 16.0, 80.0, 20.0),  # Telangana, Karnataka North
    # Eastern India & Northeast
    "64": (80.0, 20.0, 84.0, 24.0),  # Chhattisgarh, Odisha West
    "65": (80.0, 16.0, 84.0, 20.0),  # Andhra Pradesh North, Odisha South
    "73": (84.0, 20.0, 88.0, 24.0),  # Odisha Coastal, Jharkhand, West Bengal
    "78": (88.0, 24.0, 92.0, 28.0),  # Assam West, Meghalaya, Bhutan
    "83": (92.0, 24.0, 96.0, 28.0),  # Assam East, Nagaland, Arunachal Pradesh
    "84": (92.0, 20.0, 96.0, 24.0),  # Manipur, Mizoram
    # Southern India
    "48": (72.0, 12.0, 76.0, 16.0),  # Karnataka Coastal, Kerala North
    "49": (72.0, 8.0, 76.0, 12.0),   # Kerala South, Lakshadweep
    "57": (76.0, 12.0, 80.0, 16.0),  # Karnataka South, Tamil Nadu North
    "58": (76.0, 8.0, 80.0, 12.0),   # Tamil Nadu South, Kerala South
    "66": (80.0, 12.0, 84.0, 16.0),  # Andhra Pradesh / TN Coast
}

# 1:250,000 Degree Sheet Lettering Grid (A to P, column-wise downward from NW)
DEGREE_LETTERS = [
    ["A", "E", "I", "M"],  # Row 0 (Northernmost 1° lat)
    ["B", "F", "J", "N"],  # Row 1
    ["C", "G", "K", "O"],  # Row 2
    ["D", "H", "L", "P"],  # Row 3 (Southernmost 1° lat)
]

# 1:50,000 Toposheet Numbering Grid (1 to 16, column-wise downward from NW)
TOPOSHEET_NUMBERS = [
    [1, 5, 9, 13],   # Row 0 (Northernmost 15' lat)
    [2, 6, 10, 14],  # Row 1
    [3, 7, 11, 15],  # Row 2
    [4, 8, 12, 16],  # Row 3 (Southernmost 15' lat)
]


def bbox_to_polygon(minx: float, miny: float, maxx: float, maxy: float) -> Dict[str, Any]:
    """Return GeoJSON polygon coordinate ring for a bbox."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [round(minx, 6), round(miny, 6)],
                [round(maxx, 6), round(miny, 6)],
                [round(maxx, 6), round(maxy, 6)],
                [round(minx, 6), round(maxy, 6)],
                [round(minx, 6), round(miny, 6)],
            ]
        ],
    }


def bboxes_intersect(b1: Tuple[float, float, float, float], b2: Tuple[float, float, float, float]) -> bool:
    """Check if two bounding boxes [minx, miny, maxx, maxy] intersect."""
    return not (b1[2] <= b2[0] or b1[0] >= b2[2] or b1[3] <= b2[1] or b1[1] >= b2[3])


def generate_soi_grid(
    bbox: Optional[Tuple[float, float, float, float]] = None,
    include_250k: bool = True,
    include_50k: bool = True,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate GeoJSON FeatureCollection of official Survey of India toposheet footprints."""
    features: List[Dict[str, Any]] = []
    q_norm = query.strip().upper() if query else None

    for m_num, m_bounds in MILLION_SHEETS.items():
        if bbox and not bboxes_intersect(m_bounds, bbox):
            continue

        m_minx, m_miny, m_maxx, m_maxy = m_bounds

        # Loop through 4 columns and 4 rows of Degree sheets (1° x 1°)
        for r_idx in range(4):
            d_maxy = m_maxy - (r_idx * 1.0)
            d_miny = d_maxy - 1.0

            for c_idx in range(4):
                d_minx = m_minx + (c_idx * 1.0)
                d_maxx = d_minx + 1.0
                d_bounds = (d_minx, d_miny, d_maxx, d_maxy)

                if bbox and not bboxes_intersect(d_bounds, bbox):
                    continue

                letter = DEGREE_LETTERS[r_idx][c_idx]
                degree_sheet_no = f"{m_num}{letter}"

                if include_250k:
                    if not q_norm or q_norm in degree_sheet_no:
                        features.append({
                            "type": "Feature",
                            "id": degree_sheet_no,
                            "properties": {
                                "sheet_no": degree_sheet_no,
                                "name": f"SOI Degree Sheet {degree_sheet_no}",
                                "scale": "1:250,000",
                                "million_sheet": m_num,
                                "degree_sheet": degree_sheet_no,
                                "lat_extent": f"{d_miny:g}°N - {d_maxy:g}°N",
                                "lon_extent": f"{d_minx:g}°E - {d_maxx:g}°E",
                                "source": "Survey of India Standard Grid",
                            },
                            "geometry": bbox_to_polygon(d_minx, d_miny, d_maxx, d_maxy),
                        })

                if include_50k:
                    for t_r in range(4):
                        t_maxy = d_maxy - (t_r * 0.25)
                        t_miny = t_maxy - 0.25

                        for t_c in range(4):
                            t_minx = d_minx + (t_c * 0.25)
                            t_maxx = t_minx + 0.25
                            t_bounds = (t_minx, t_miny, t_maxx, t_maxy)

                            if bbox and not bboxes_intersect(t_bounds, bbox):
                                continue

                            t_num = TOPOSHEET_NUMBERS[t_r][t_c]
                            topo_sheet_no = f"{degree_sheet_no}/{t_num}"

                            if q_norm and q_norm not in topo_sheet_no and q_norm not in degree_sheet_no:
                                continue

                            features.append({
                                "type": "Feature",
                                "id": topo_sheet_no,
                                "properties": {
                                    "sheet_no": topo_sheet_no,
                                    "osm_no": topo_sheet_no,
                                    "name": f"SOI Topo Sheet {topo_sheet_no}",
                                    "scale": "1:50,000",
                                    "million_sheet": m_num,
                                    "degree_sheet": degree_sheet_no,
                                    "lat_extent": f"{t_miny:g}°N - {t_maxy:g}°N",
                                    "lon_extent": f"{t_minx:g}°E - {t_maxx:g}°E",
                                    "source": "Survey of India Standard Grid",
                                },
                                "geometry": bbox_to_polygon(t_minx, t_miny, t_maxx, t_maxy),
                            })

    return {"type": "FeatureCollection", "features": features}
