"""ForecastGuard V2 — Atmospheric & Environmental Conditioning Intelligence.

Extracts real, physically meaningful environmental conditioning signals
from verified forecast fields (e.g. NCMRWF NEPS MSLP grids) and enforces
strict scientific data-availability gates for unprovided atmospheric parameters
(850 hPa wind, 200/250 hPa wind, vertical wind shear, mid-level humidity, SST).

Invariants enforced:
1. Zero fabrication: If an atmospheric parameter is absent from the inspected archive,
   it is explicitly designated as UNAVAILABLE / INSUFFICIENT_EVIDENCE.
2. Anti-leakage: All features at forecast cutoff T use only information available <= T.
3. Scientific Claim Firewall: Environmental signals are conditioning or associative evidence,
   NEVER asserted as deterministic "causes" of forecast failure.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
import numpy as np

EnvironmentalState = Literal[
    "SYMMETRIC_DEEP_PRESSURE_STRUCTURE",
    "MARGINAL_PRESSURE_STRUCTURE",
    "ASYMMETRIC_WEAK_PRESSURE_STRUCTURE",
    "INSUFFICIENT_EVIDENCE",
]

AvailabilityStatus = Literal["AVAILABLE", "UNAVAILABLE", "INSUFFICIENT_EVIDENCE"]


@dataclass(frozen=True)
class VariableAvailabilityReport:
    """Rigorous audit record for an atmospheric variable within the archive."""

    variable_name: str
    status: AvailabilityStatus
    exact_source: str
    level_type: str
    native_resolution: str
    temporal_cadence: str
    valid_time_alignment: str
    units: str
    cases_coverage_count: int
    total_cases_count: int
    missingness_percent: float
    respects_replay_boundary: bool
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Authoritative audit of the 5 requested variables against the verified cyclone archive
ATMOSPHERIC_VARIABLE_AUDIT: Dict[str, VariableAvailabilityReport] = {
    "wind_850hpa": VariableAvailabilityReport(
        variable_name="850-hPa Horizontal Wind",
        status="UNAVAILABLE",
        exact_source="None in local NCMRWF NEPS cyclone archive",
        level_type="isobaricInhPa (850)",
        native_resolution="N/A",
        temporal_cadence="N/A",
        valid_time_alignment="N/A",
        units="m/s",
        cases_coverage_count=0,
        total_cases_count=6,
        missingness_percent=100.0,
        respects_replay_boundary=True,
        reason="Local TIGGE cyclone archive contains single-level MSLP only. Upper-air sounding levels are not in the local dataset.",
    ),
    "wind_200hpa": VariableAvailabilityReport(
        variable_name="200/250-hPa Horizontal Wind",
        status="UNAVAILABLE",
        exact_source="None in local NCMRWF NEPS cyclone archive",
        level_type="isobaricInhPa (200/250)",
        native_resolution="N/A",
        temporal_cadence="N/A",
        valid_time_alignment="N/A",
        units="m/s",
        cases_coverage_count=0,
        total_cases_count=6,
        missingness_percent=100.0,
        respects_replay_boundary=True,
        reason="Upper-tropospheric wind vectors are not present in the local single-level archive.",
    ),
    "vertical_wind_shear": VariableAvailabilityReport(
        variable_name="Deep-Layer Vertical Wind Shear (850-200 hPa)",
        status="UNAVAILABLE",
        exact_source="Derived (Vector difference V200 - V850)",
        level_type="differential (200 hPa minus 850 hPa)",
        native_resolution="N/A",
        temporal_cadence="N/A",
        valid_time_alignment="N/A",
        units="m/s (or kt)",
        cases_coverage_count=0,
        total_cases_count=6,
        missingness_percent=100.0,
        respects_replay_boundary=True,
        reason="Cannot derive vertical wind shear because neither 850 hPa nor 200 hPa wind fields exist in the local archive.",
    ),
    "mid_tropospheric_humidity": VariableAvailabilityReport(
        variable_name="Mid-Tropospheric Relative Humidity (700-500 hPa)",
        status="UNAVAILABLE",
        exact_source="None in local NCMRWF NEPS cyclone archive",
        level_type="isobaricInhPa (700, 500)",
        native_resolution="N/A",
        temporal_cadence="N/A",
        valid_time_alignment="N/A",
        units="%",
        cases_coverage_count=0,
        total_cases_count=6,
        missingness_percent=100.0,
        respects_replay_boundary=True,
        reason="Specific or relative humidity at mid-tropospheric levels is not present in the local single-level archive.",
    ),
    "sea_surface_temperature": VariableAvailabilityReport(
        variable_name="Sea Surface Temperature (SST)",
        status="UNAVAILABLE",
        exact_source="None in local NCMRWF NEPS cyclone archive",
        level_type="surface ocean",
        native_resolution="N/A",
        temporal_cadence="N/A",
        valid_time_alignment="N/A",
        units="°C (or K)",
        cases_coverage_count=0,
        total_cases_count=6,
        missingness_percent=100.0,
        respects_replay_boundary=True,
        reason="Sea surface temperature field is absent from the local single-level TIGGE cyclone archive.",
    ),
    "surface_mslp_field": VariableAvailabilityReport(
        variable_name="Mean Sea Level Pressure (msl)",
        status="AVAILABLE",
        exact_source="TIGGE NCMRWF NEPS (origin: dems)",
        level_type="meanSea",
        native_resolution="0.5° × 0.5° latitude/longitude",
        temporal_cadence="6-hourly (06h to 48h)",
        valid_time_alignment="Exact synoptic match (00, 06, 12, 18 UTC)",
        units="Pa (converted to hPa via / 100.0)",
        cases_coverage_count=6,
        total_cases_count=6,
        missingness_percent=0.0,
        respects_replay_boundary=True,
        reason="Full 11-member ensemble grid verified across all 6 historical cyclone cases.",
    ),
}


@dataclass(frozen=True)
class EnvironmentalIntelligenceResult:
    """Deterministic environmental intelligence computed from available forecast data."""

    state: EnvironmentalState
    state_description: str
    pressure_depth_hpa: Optional[float]
    pressure_gradient_hpa_per_100km: Optional[float]
    gradient_asymmetry_hpa_per_100km: Optional[float]
    gradient_trend_hpa_per_100km: Optional[float]
    core_pressure_hpa: Optional[float]
    peripheral_pressure_hpa: Optional[float]
    annulus_inner_radius_km: float
    annulus_outer_radius_km: float
    upper_air_shear_status: AvailabilityStatus
    mid_level_humidity_status: AvailabilityStatus
    sst_status: AvailabilityStatus
    validation_status: Literal["VALIDATED", "EXPERIMENTAL", "INSUFFICIENT_EVIDENCE"]
    provenance: str
    scientific_provenance_note: str = (
        "Derived from NCMRWF NEPS ensemble MSLP pressure-gradient geometry. "
        "NOT a direct measurement of vertical wind shear, upper-air wind, or humidity."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between coordinates in kilometers (Earth radius 6371.0 km)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return 6371.0 * c


def compute_environmental_pressure_depth(
    center_lat: float,
    center_lon: float,
    center_pressure_hpa: float,
    lats: np.ndarray,
    lons: np.ndarray,
    mslp_hpa_grid: np.ndarray,
    inner_radius_km: float = 300.0,
    outer_radius_km: float = 600.0,
) -> Tuple[float, float]:
    """Compute outer peripheral environmental pressure and pressure depth around the vortex.

    Parameters
    ----------
    center_lat : float
        Latitude of the detected cyclonic center.
    center_lon : float
        Longitude of the detected cyclonic center.
    center_pressure_hpa : float
        Central minimum MSLP in hPa.
    lats : np.ndarray
        1D or 2D array of grid latitudes.
    lons : np.ndarray
        1D or 2D array of grid longitudes.
    mslp_hpa_grid : np.ndarray
        2D grid of mean sea level pressure in hPa.
    inner_radius_km : float
        Inner boundary of synoptic environment annulus (default 300 km).
    outer_radius_km : float
        Outer boundary of synoptic environment annulus (default 600 km).

    Returns
    -------
    Tuple[float, float]
        (peripheral_pressure_hpa, pressure_depth_hpa)
    """
    if inner_radius_km >= outer_radius_km:
        raise ValueError("inner_radius_km must be strictly less than outer_radius_km")

    # If coordinates are 1D, meshgrid them
    if lats.ndim == 1 and lons.ndim == 1:
        grid_lons, grid_lats = np.meshgrid(lons, lats)
    else:
        grid_lats = lats
        grid_lons = lons

    # Approximate distance using Haversine vectorization or equirectangular approximation for grid filter
    # To be mathematically exact and efficient on moderate grid sizes (e.g. 50x50):
    phi1 = np.radians(center_lat)
    phi2 = np.radians(grid_lats)
    dphi = np.radians(grid_lats - center_lat)
    dlam = np.radians(grid_lons - center_lon)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2.0) ** 2
    dist_km = 6371.0 * 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))

    # Mask the outer synoptic annulus
    annulus_mask = (dist_km >= inner_radius_km) & (dist_km <= outer_radius_km) & np.isfinite(mslp_hpa_grid)

    if not np.any(annulus_mask):
        # If no cells fall in the annulus, return nominal peripheral pressure matching center
        return center_pressure_hpa, 0.0

    peripheral_pressure_hpa = float(np.nanmean(mslp_hpa_grid[annulus_mask]))
    pressure_depth_hpa = max(0.0, peripheral_pressure_hpa - center_pressure_hpa)

    return peripheral_pressure_hpa, pressure_depth_hpa


def compute_radial_pressure_gradient(
    pressure_depth_hpa: float,
    mean_annulus_radius_km: float = 450.0,
) -> float:
    """Compute radial pressure gradient from vortex center to synoptic annulus.

    Gradient is normalized to hPa per 100 km:
    gradient = (depth_hpa / radius_km) * 100.0
    """
    if mean_annulus_radius_km <= 0:
        return 0.0
    return float((pressure_depth_hpa / mean_annulus_radius_km) * 100.0)


def compute_pressure_gradient_asymmetry(
    center_lat: float,
    center_lon: float,
    lats: np.ndarray,
    lons: np.ndarray,
    mslp_hpa_grid: np.ndarray,
    inner_radius_km: float = 300.0,
    outer_radius_km: float = 600.0,
) -> float:
    """Compute directional pressure gradient asymmetry in the outer synoptic annulus.

    Partitions the annulus into four quadrants (North, East, South, West).
    Computes directional difference across North-South and East-West to detect
    environmental ridge/trough steering dipoles.

    Returns asymmetry magnitude in hPa / 100 km.
    """
    if lats.ndim == 1 and lons.ndim == 1:
        grid_lons, grid_lats = np.meshgrid(lons, lats)
    else:
        grid_lats = lats
        grid_lons = lons

    phi1 = np.radians(center_lat)
    phi2 = np.radians(grid_lats)
    dphi = np.radians(grid_lats - center_lat)
    dlam = np.radians(grid_lons - center_lon)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2.0) ** 2
    dist_km = 6371.0 * 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))

    annulus = (dist_km >= inner_radius_km) & (dist_km <= outer_radius_km) & np.isfinite(mslp_hpa_grid)

    if not np.any(annulus):
        return 0.0

    # Quadrant masks
    north_mask = annulus & (grid_lats >= center_lat)
    south_mask = annulus & (grid_lats < center_lat)
    east_mask = annulus & (grid_lons >= center_lon)
    west_mask = annulus & (grid_lons < center_lon)

    p_north = float(np.nanmean(mslp_hpa_grid[north_mask])) if np.any(north_mask) else float(np.nanmean(mslp_hpa_grid[annulus]))
    p_south = float(np.nanmean(mslp_hpa_grid[south_mask])) if np.any(south_mask) else float(np.nanmean(mslp_hpa_grid[annulus]))
    p_east = float(np.nanmean(mslp_hpa_grid[east_mask])) if np.any(east_mask) else float(np.nanmean(mslp_hpa_grid[annulus]))
    p_west = float(np.nanmean(mslp_hpa_grid[west_mask])) if np.any(west_mask) else float(np.nanmean(mslp_hpa_grid[annulus]))

    # Cross-dipole gradients over diameter (2 * 450 km = 900 km)
    delta_ns = abs(p_north - p_south)
    delta_ew = abs(p_east - p_west)

    grad_ns = (delta_ns / 900.0) * 100.0
    grad_ew = (delta_ew / 900.0) * 100.0

    asymmetry = float(math.sqrt(grad_ns**2 + grad_ew**2))
    return round(asymmetry, 3)


def classify_environmental_state(
    pressure_gradient: Optional[float],
    asymmetry: Optional[float],
    pressure_depth: Optional[float],
    gradient_trend: Optional[float] = None,
) -> Tuple[EnvironmentalState, str]:
    """Deterministically classify environmental state from surface pressure kinematics.

    Thresholds strictly evaluate MSLP-derived pressure-gradient geometry:
    - Asymmetric or Weak: asymmetry >= 2.2 hPa/100km or gradient < 1.5 hPa/100km or gradient_trend < -0.8
    - Symmetric & Deep: gradient >= 3.5 hPa/100km or depth >= 25.0 hPa (with asymmetry < 2.2)
    - Marginal Pressure Structure: moderate environmental gradient [1.5, 3.5) with low asymmetry (< 2.2)
    - Insufficient Evidence: values missing or outside tracking domain
    """
    if pressure_gradient is None or pressure_depth is None:
        return (
            "INSUFFICIENT_EVIDENCE",
            "Insufficient environmental pressure data to classify synoptic pressure structure.",
        )

    asym = asymmetry if asymmetry is not None else 0.0

    if asym >= 2.2:
        return (
            "ASYMMETRIC_WEAK_PRESSURE_STRUCTURE",
            f"Asymmetric synoptic pressure pattern ({asym:.2f} hPa/100km) indicates non-uniform pressure-gradient geometry.",
        )

    if pressure_gradient < 1.5 or (gradient_trend is not None and gradient_trend < -0.8):
        return (
            "ASYMMETRIC_WEAK_PRESSURE_STRUCTURE",
            f"Weak radial pressure gradient ({pressure_gradient:.2f} hPa/100km) indicates diffuse synoptic pressure structure.",
        )

    if pressure_gradient >= 3.5 or pressure_depth >= 25.0:
        return (
            "SYMMETRIC_DEEP_PRESSURE_STRUCTURE",
            f"Deep cyclonic core ({pressure_depth:.1f} hPa depth) and steep radial gradient ({pressure_gradient:.2f} hPa/100km) indicate symmetric, well-developed pressure structure.",
        )

    return (
        "MARGINAL_PRESSURE_STRUCTURE",
        f"Moderate environmental gradient ({pressure_gradient:.2f} hPa/100km) with low asymmetry ({asym:.2f} hPa/100km) indicates marginal pressure-gradient geometry.",
    )


def extract_environmental_intelligence_from_grid(
    center_lat: float,
    center_lon: float,
    center_pressure_hpa: float,
    lats: np.ndarray,
    lons: np.ndarray,
    mslp_hpa_grid: np.ndarray,
    prior_gradient: Optional[float] = None,
    inner_radius_km: float = 300.0,
    outer_radius_km: float = 600.0,
    provenance_source: str = "TIGGE NCMRWF NEPS MSLP (0.5°)",
) -> EnvironmentalIntelligenceResult:
    """Extract complete deterministic environmental intelligence from verified MSLP grid."""
    peripheral_hpa, depth_hpa = compute_environmental_pressure_depth(
        center_lat=center_lat,
        center_lon=center_lon,
        center_pressure_hpa=center_pressure_hpa,
        lats=lats,
        lons=lons,
        mslp_hpa_grid=mslp_hpa_grid,
        inner_radius_km=inner_radius_km,
        outer_radius_km=outer_radius_km,
    )

    mean_radius = (inner_radius_km + outer_radius_km) / 2.0
    gradient_hpa_100km = compute_radial_pressure_gradient(depth_hpa, mean_radius)

    asymmetry_hpa_100km = compute_pressure_gradient_asymmetry(
        center_lat=center_lat,
        center_lon=center_lon,
        lats=lats,
        lons=lons,
        mslp_hpa_grid=mslp_hpa_grid,
        inner_radius_km=inner_radius_km,
        outer_radius_km=outer_radius_km,
    )

    gradient_trend = None
    if prior_gradient is not None:
        gradient_trend = round(gradient_hpa_100km - prior_gradient, 2)

    state, desc = classify_environmental_state(
        pressure_gradient=gradient_hpa_100km,
        asymmetry=asymmetry_hpa_100km,
        pressure_depth=depth_hpa,
        gradient_trend=gradient_trend,
    )

    return EnvironmentalIntelligenceResult(
        state=state,
        state_description=desc,
        pressure_depth_hpa=round(depth_hpa, 1),
        pressure_gradient_hpa_per_100km=round(gradient_hpa_100km, 2),
        gradient_asymmetry_hpa_per_100km=asymmetry_hpa_100km,
        gradient_trend_hpa_per_100km=gradient_trend,
        core_pressure_hpa=round(center_pressure_hpa, 1),
        peripheral_pressure_hpa=round(peripheral_hpa, 1),
        annulus_inner_radius_km=inner_radius_km,
        annulus_outer_radius_km=outer_radius_km,
        upper_air_shear_status="UNAVAILABLE",
        mid_level_humidity_status="UNAVAILABLE",
        sst_status="UNAVAILABLE",
        validation_status="EXPERIMENTAL",
        provenance=provenance_source,
    )


def extract_fallback_environmental_insufficient(
    reason: str = "Regional grid or vortex fix outside supported cyclone domain.",
) -> EnvironmentalIntelligenceResult:
    """Return clean, locked INSUFFICIENT_EVIDENCE environmental intelligence with zero fake data."""
    return EnvironmentalIntelligenceResult(
        state="INSUFFICIENT_EVIDENCE",
        state_description=reason,
        pressure_depth_hpa=None,
        pressure_gradient_hpa_per_100km=None,
        gradient_asymmetry_hpa_per_100km=None,
        gradient_trend_hpa_per_100km=None,
        core_pressure_hpa=None,
        peripheral_pressure_hpa=None,
        annulus_inner_radius_km=300.0,
        annulus_outer_radius_km=600.0,
        upper_air_shear_status="UNAVAILABLE",
        mid_level_humidity_status="UNAVAILABLE",
        sst_status="UNAVAILABLE",
        validation_status="INSUFFICIENT_EVIDENCE",
        provenance="None (Outside Supported Basin)",
    )
