from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.core.satellites.catalog import (
    master_catalog,
    MasterMission,
    MissionBand,
    DOMAINS,
    MASTER_MISSIONS,
)


class BandDefinition(BaseModel):
    id: str
    name: str
    description: str
    wavelength_um: Optional[str] = None
    resolution_m: float
    approx_size_bytes: int
    is_default: bool = False


class SatelliteConstellation(BaseModel):
    id: str
    collection_id: str
    name: str
    sensor_type: str  # "OPTICAL", "SAR", "DEM", "CLIMATE", "ALTIMETRY", etc.
    agency: str
    resolution_meters: float
    description: str
    supports_cloud_filter: bool = True
    supports_datetime_filter: bool = True
    bands: List[BandDefinition] = Field(default_factory=list)


def mission_to_constellation(m: MasterMission) -> SatelliteConstellation:
    return SatelliteConstellation(
        id=m.id,
        collection_id=m.collection_id,
        name=m.name,
        sensor_type=m.domain,
        agency=m.agency,
        resolution_meters=m.resolution_meters,
        description=m.description,
        supports_cloud_filter=m.supports_cloud_filter,
        supports_datetime_filter=m.supports_datetime_filter,
        bands=[
            BandDefinition(
                id=b.id,
                name=b.name,
                description=b.description,
                wavelength_um=b.wavelength_um,
                resolution_m=b.resolution_m,
                approx_size_bytes=b.approx_size_bytes,
                is_default=b.is_default,
            )
            for b in m.bands
        ],
    )


DEFAULT_CONSTELLATIONS: List[SatelliteConstellation] = [
    mission_to_constellation(m) for m in master_catalog.list_missions()
]


class ConstellationRegistry:
    def __init__(self):
        self._constellations: Dict[str, SatelliteConstellation] = {
            m.id: mission_to_constellation(m) for m in master_catalog.list_missions()
        }
        self._by_collection: Dict[str, SatelliteConstellation] = {
            m.collection_id: mission_to_constellation(m) for m in master_catalog.list_missions()
        }

    def list_constellations(self) -> List[SatelliteConstellation]:
        return list(self._constellations.values())

    def get_by_id(self, constellation_id: str) -> Optional[SatelliteConstellation]:
        return self._constellations.get(constellation_id)

    def get_by_collection(self, collection_id: str) -> Optional[SatelliteConstellation]:
        return self._by_collection.get(collection_id)


constellation_registry = ConstellationRegistry()
