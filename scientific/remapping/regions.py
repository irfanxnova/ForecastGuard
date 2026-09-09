"""Predefined Analytical Regional Definitions and Spatial Masking Utilities.

ForecastGuard Predefined Analytical Regions for South Asia and adjacent marine basins.
Establishes principled, reproducible spatial partitions for prospective regional forecast
reliability assessment without arbitrary screenshot-only boundaries.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass(frozen=True)
class PredefinedRegion:
    """Predefined analytical region specification."""

    region_id: str
    name: str
    short_label: str
    category: str  # "LAND" or "MARITIME"
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    center_lat: float
    center_lon: float
    boundary_polygon: Tuple[Tuple[float, float], ...]  # (lat, lon) tuples

    def contains_point(self, lat: float, lon: float) -> bool:
        """Check if a coordinate falls within the region bounding box and polygon."""
        if not (self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon):
            return False
        
        # Ray casting algorithm for polygon point-in-polygon
        poly = self.boundary_polygon
        n = len(poly)
        inside = False
        p1_lat, p1_lon = poly[0]
        for i in range(1, n + 1):
            p2_lat, p2_lon = poly[i % n]
            if lon > min(p1_lon, p2_lon):
                if lon <= max(p1_lon, p2_lon):
                    if lat <= max(p1_lat, p2_lat):
                        if p1_lon != p2_lon:
                            lat_inters = (lon - p1_lon) * (p2_lat - p1_lat) / (p2_lon - p1_lon) + p1_lat
                        if p1_lat == p2_lat or lat <= lat_inters:
                            inside = not inside
            p1_lat, p1_lon = p2_lat, p2_lon
        return inside


# ForecastGuard Predefined Analytical Regions for South Asia / Northern Indian Ocean
PREDEFINED_REGIONS: Dict[str, PredefinedRegion] = {
    "MAR_BOB": PredefinedRegion(
        region_id="MAR_BOB",
        name="Bay of Bengal Basin",
        short_label="Bay of Bengal",
        category="MARITIME",
        min_lat=8.0,
        max_lat=22.5,
        min_lon=80.0,
        max_lon=95.0,
        center_lat=15.0,
        center_lon=88.0,
        boundary_polygon=(
            (8.0, 80.0),
            (15.0, 80.0),
            (21.0, 86.5),
            (22.5, 91.0),
            (20.0, 94.0),
            (14.0, 95.0),
            (8.0, 93.0),
            (8.0, 80.0),
        ),
    ),
    "MAR_AS": PredefinedRegion(
        region_id="MAR_AS",
        name="Arabian Sea Basin",
        short_label="Arabian Sea",
        category="MARITIME",
        min_lat=8.0,
        max_lat=24.5,
        min_lon=55.0,
        max_lon=74.0,
        center_lat=16.0,
        center_lon=65.0,
        boundary_polygon=(
            (8.0, 55.0),
            (16.0, 55.0),
            (24.5, 62.0),
            (24.0, 69.0),
            (20.0, 72.5),
            (12.0, 74.0),
            (8.0, 74.0),
            (8.0, 55.0),
        ),
    ),
    "IND_ENE": PredefinedRegion(
        region_id="IND_ENE",
        name="East & Northeast India",
        short_label="East & NE India",
        category="LAND",
        min_lat=20.0,
        max_lat=29.0,
        min_lon=83.0,
        max_lon=97.0,
        center_lat=24.5,
        center_lon=89.5,
        boundary_polygon=(
            (20.0, 83.0),
            (26.0, 83.0),
            (27.5, 88.0),
            (29.0, 94.0),
            (27.0, 97.0),
            (23.0, 93.0),
            (21.5, 87.0),
            (20.0, 83.0),
        ),
    ),
    "IND_SOU": PredefinedRegion(
        region_id="IND_SOU",
        name="South Peninsular India",
        short_label="South Peninsula",
        category="LAND",
        min_lat=8.0,
        max_lat=18.5,
        min_lon=74.0,
        max_lon=83.5,
        center_lat=13.5,
        center_lon=78.5,
        boundary_polygon=(
            (8.0, 77.0),
            (11.0, 75.0),
            (15.0, 74.0),
            (18.5, 78.0),
            (18.0, 83.5),
            (13.5, 80.5),
            (9.0, 79.5),
            (8.0, 77.0),
        ),
    ),
    "IND_CEN": PredefinedRegion(
        region_id="IND_CEN",
        name="Central India",
        short_label="Central India",
        category="LAND",
        min_lat=18.0,
        max_lat=26.0,
        min_lon=73.0,
        max_lon=86.0,
        center_lat=22.0,
        center_lon=79.5,
        boundary_polygon=(
            (18.0, 73.0),
            (23.0, 73.0),
            (26.0, 78.0),
            (25.5, 84.5),
            (21.5, 86.0),
            (18.5, 80.0),
            (18.0, 73.0),
        ),
    ),
    "IND_WST": PredefinedRegion(
        region_id="IND_WST",
        name="West Coast & Gujarat",
        short_label="West Coast",
        category="LAND",
        min_lat=17.5,
        max_lat=25.0,
        min_lon=68.0,
        max_lon=74.5,
        center_lat=21.5,
        center_lon=71.5,
        boundary_polygon=(
            (17.5, 73.0),
            (20.0, 72.5),
            (23.5, 68.0),
            (25.0, 71.0),
            (24.0, 74.5),
            (19.0, 74.0),
            (17.5, 73.0),
        ),
    ),
    "IND_NW": PredefinedRegion(
        region_id="IND_NW",
        name="Northwest India",
        short_label="Northwest India",
        category="LAND",
        min_lat=24.0,
        max_lat=36.0,
        min_lon=68.0,
        max_lon=80.5,
        center_lat=30.0,
        center_lon=74.5,
        boundary_polygon=(
            (24.0, 68.0),
            (28.0, 69.0),
            (34.0, 73.5),
            (36.0, 77.0),
            (31.0, 80.5),
            (26.0, 78.5),
            (24.0, 73.0),
            (24.0, 68.0),
        ),
    ),
}

# Backward compatibility aliases
MeteorologicalRegion = PredefinedRegion
METEOROLOGICAL_REGIONS = PREDEFINED_REGIONS


def get_all_regions() -> List[PredefinedRegion]:
    """Return all ForecastGuard predefined analytical regions."""
    return list(PREDEFINED_REGIONS.values())


def get_region_by_id(region_id: str) -> Optional[PredefinedRegion]:
    """Retrieve predefined region definition by ID."""
    return PREDEFINED_REGIONS.get(region_id.upper())


def check_domain_overlap(
    first_lat: float,
    last_lat: float,
    first_lon: float,
    last_lon: float,
    region: MeteorologicalRegion,
) -> Tuple[bool, float]:
    """Calculate overlap area between a forecast grid bounding box and a region bbox.

    Returns:
        (is_supported, coverage_percentage)
    """
    g_min_lat = min(first_lat, last_lat)
    g_max_lat = max(first_lat, last_lat)
    g_min_lon = min(first_lon, last_lon)
    g_max_lon = max(first_lon, last_lon)

    # Intersection bounds
    i_min_lat = max(g_min_lat, region.min_lat)
    i_max_lat = min(g_max_lat, region.max_lat)
    i_min_lon = max(g_min_lon, region.min_lon)
    i_max_lon = min(g_max_lon, region.max_lon)

    if i_min_lat >= i_max_lat or i_min_lon >= i_max_lon:
        return False, 0.0

    intersection_area = (i_max_lat - i_min_lat) * (i_max_lon - i_min_lon)
    region_area = (region.max_lat - region.min_lat) * (region.max_lon - region.min_lon)

    coverage_percent = min(100.0, max(0.0, (intersection_area / region_area) * 100.0))
    # Threshold for operational support: at least 15% overlap
    is_supported = coverage_percent >= 15.0
    return is_supported, round(coverage_percent, 1)


def create_region_grid_mask(
    lat_grid: np.ndarray,
    lon_grid: np.ndarray,
    region: MeteorologicalRegion,
) -> np.ndarray:
    """Create boolean mask for 2D lat/lon coordinate grids falling within region.

    Args:
        lat_grid: 2D array of latitudes (nj, ni) or 1D array (nj,)
        lon_grid: 2D array of longitudes (nj, ni) or 1D array (ni,)
        region: MeteorologicalRegion instance

    Returns:
        Boolean mask array of shape matching grid
    """
    if lat_grid.ndim == 1 and lon_grid.ndim == 1:
        # Construct 2D grid from 1D coordinate vectors
        lon_2d, lat_2d = np.meshgrid(lon_grid, lat_grid)
    else:
        lat_2d = lat_grid
        lon_2d = lon_grid

    # Bounding box filter (fast vectorised check)
    bbox_mask = (
        (lat_2d >= region.min_lat)
        & (lat_2d <= region.max_lat)
        & (lon_2d >= region.min_lon)
        & (lon_2d <= region.max_lon)
    )

    # For points inside bbox, run exact polygon test
    result_mask = np.zeros_like(bbox_mask, dtype=bool)
    candidate_indices = np.argwhere(bbox_mask)
    for row, col in candidate_indices:
        if region.contains_point(float(lat_2d[row, col]), float(lon_2d[row, col])):
            result_mask[row, col] = True

    return result_mask
