"""Ensemble rainfall feature extraction for ForecastGuard.

Extracts scientifically meaningful ensemble statistics from TP (total precipitation)
fields without using observations or future information.

This module calculates:
- Ensemble central statistics (mean, median, percentiles)
- Ensemble spread features (std, range, IQR)
- Ensemble shape descriptors (skewness, coefficient of variation)
- Event probability features (rain thresholds)
- Spatial features (gradients)
- Ensemble geometry features (disagreement, member difference)

All features respect AGENTS.md constraints:
- No fabricated data
- No silent transformations
- NaNs preserved appropriately
- Zero rainfall distinguished from missing data
- Numerical safety for edge cases

Each grid cell's feature set is independent; spatial features use local neighbors
on the regular lat/lon grid (not physical distance normalized).
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class EnsembleRainfallFeatures:
    """Complete set of ensemble rainfall features for a single forecast.

    Features are structured as 2D arrays matching the forecast grid (latitude x longitude),
    or scalar metadata fields. All grid-based arrays have shape (n_lat, n_lon).

    This is not a large data object; it holds only derived statistics, not the raw
    ensemble member fields.
    """

    # ---------------------------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------------------------

    forecast_date: int
    """GRIB dataDate (YYYYMMDD)."""

    forecast_time: int
    """GRIB dataTime (HHMM as integer)."""

    forecast_step: int
    """Forecast lead time in hours."""

    forecast_step_type: str
    """Accumulation type (e.g., 'accum' for 0–24h)."""

    initialization_time: Optional[datetime] = None
    """Parsed datetime of forecast initialization (UTC aware)."""

    member_count: int = 0
    """Total number of ensemble members in the input."""

    valid_member_count: int = 0
    """Number of members with at least one valid value at any grid point."""

    grid_shape: Tuple[int, int] = (0, 0)
    """Grid shape (n_lat, n_lon)."""

    grid_first_lat: Optional[float] = None
    """Latitude of first grid point (degrees)."""

    grid_first_lon: Optional[float] = None
    """Longitude of first grid point (degrees)."""

    grid_last_lat: Optional[float] = None
    """Latitude of last grid point (degrees)."""

    grid_last_lon: Optional[float] = None
    """Longitude of last grid point (degrees)."""

    grid_lat_increment: Optional[float] = None
    """Latitude grid spacing (degrees, j_increment from GRIB)."""

    grid_lon_increment: Optional[float] = None
    """Longitude grid spacing (degrees, i_increment from GRIB)."""

    # ---------------------------------------------------------------------------
    # Central Statistics (grid)
    # ---------------------------------------------------------------------------

    ensemble_mean: np.ndarray = field(default_factory=lambda: np.array([]))
    """Ensemble mean TP at each grid point (shape: grid_shape)."""

    ensemble_median: np.ndarray = field(default_factory=lambda: np.array([]))
    """Ensemble median TP at each grid point."""

    ensemble_min: np.ndarray = field(default_factory=lambda: np.array([]))
    """Ensemble minimum TP at each grid point."""

    ensemble_max: np.ndarray = field(default_factory=lambda: np.array([]))
    """Ensemble maximum TP at each grid point."""

    # ---------------------------------------------------------------------------
    # Spread Statistics (grid)
    # ---------------------------------------------------------------------------

    ensemble_std: np.ndarray = field(default_factory=lambda: np.array([]))
    """Ensemble standard deviation of TP at each grid point."""

    ensemble_range: np.ndarray = field(default_factory=lambda: np.array([]))
    """Ensemble range (max - min) TP at each grid point."""

    ensemble_iqr: np.ndarray = field(default_factory=lambda: np.array([]))
    """Interquartile range (p75 - p25) at each grid point."""

    # ---------------------------------------------------------------------------
    # Percentiles (grid)
    # ---------------------------------------------------------------------------

    ensemble_p10: np.ndarray = field(default_factory=lambda: np.array([]))
    """10th percentile of TP at each grid point."""

    ensemble_p25: np.ndarray = field(default_factory=lambda: np.array([]))
    """25th percentile of TP at each grid point."""

    ensemble_p75: np.ndarray = field(default_factory=lambda: np.array([]))
    """75th percentile of TP at each grid point."""

    ensemble_p90: np.ndarray = field(default_factory=lambda: np.array([]))
    """90th percentile of TP at each grid point."""

    # ---------------------------------------------------------------------------
    # Shape Descriptors (grid)
    # ---------------------------------------------------------------------------

    coefficient_of_variation: np.ndarray = field(default_factory=lambda: np.array([]))
    """CV = std / mean (NaN where mean ≈ 0, handles zero-rainfall cells)."""

    ensemble_skewness: np.ndarray = field(default_factory=lambda: np.array([]))
    """Fisher's skewness (third moment), NaN where variance ≈ 0."""

    # ---------------------------------------------------------------------------
    # Event Probability Features (grid)
    # ---------------------------------------------------------------------------

    probability_rain_gt_1mm: np.ndarray = field(default_factory=lambda: np.array([]))
    """Fraction of members with TP > 1 mm at each grid point."""

    probability_rain_gt_10mm: np.ndarray = field(default_factory=lambda: np.array([]))
    """Fraction of members with TP > 10 mm at each grid point."""

    probability_rain_gt_25mm: np.ndarray = field(default_factory=lambda: np.array([]))
    """Fraction of members with TP > 25 mm at each grid point."""

    probability_rain_gt_50mm: np.ndarray = field(default_factory=lambda: np.array([]))
    """Fraction of members with TP > 50 mm at each grid point."""

    probability_rain_gt_100mm: np.ndarray = field(default_factory=lambda: np.array([]))
    """Fraction of members with TP > 100 mm at each grid point."""

    # ---------------------------------------------------------------------------
    # Spatial Features (grid)
    # ---------------------------------------------------------------------------

    gradient_magnitude: np.ndarray = field(default_factory=lambda: np.array([]))
    """Magnitude of spatial gradient of ensemble_mean.

    Computed as sqrt(dlat² + dlon²), where dlat and dlon are computed using
    finite differences on the regular lat/lon grid (not distance-normalized).
    Edge cells use one-sided differences. NaN where gradient undefined.
    """

    latitude_gradient: np.ndarray = field(default_factory=lambda: np.array([]))
    """North-south gradient component (Δ mean / Δ lat in grid space)."""

    longitude_gradient: np.ndarray = field(default_factory=lambda: np.array([]))
    """East-west gradient component (Δ mean / Δ lon in grid space)."""

    # ---------------------------------------------------------------------------
    # Ensemble Geometry Features (grid)
    # ---------------------------------------------------------------------------

    mean_pairwise_member_difference: np.ndarray = field(default_factory=lambda: np.array([]))
    """Mean absolute pairwise difference among all ensemble members.

    For each grid cell, computes mean(|m_i - m_j|) over all distinct pairs (i,j).
    Measures overall member-to-member disagreement. Ignores NaN members.
    """

    maximum_ensemble_gap: np.ndarray = field(default_factory=lambda: np.array([]))
    """Maximum gap between adjacent sorted ensemble members at each grid point.

    Measures ensemble clustering and bimodality. Large gap indicates ensemble splits
    into distinct clusters. Small gap indicates ensemble consensus. Computed as
    max(sorted_members[i+1] - sorted_members[i]).
    """

    member_agreement_fraction: np.ndarray = field(default_factory=lambda: np.array([]))
    """Fraction of member pairs within 25% of the ensemble mean.

    Defines agreement as |m_i - m_j| < 0.25 * mean. At zero-rainfall cells where
    mean < epsilon, uses absolute threshold |m_i - m_j| < 0.01 mm.
    High values (close to 1) suggest strong consensus.
    """

    # ---------------------------------------------------------------------------
    # Provenance and Metadata
    # ---------------------------------------------------------------------------

    feature_names: List[str] = field(default_factory=list)
    """Ordered list of feature names used in extraction."""

    source_metadata: Dict[str, Any] = field(default_factory=dict)
    """GRIB metadata from input messages (for audit trail)."""

    extraction_timestamp: Optional[datetime] = None
    """UTC datetime when features were extracted."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, converting arrays to lists for serialization.

        WARNING: This is useful for debugging but will be very large for full grids.
        Prefer accessing individual features directly.
        """
        result = asdict(self)
        for key in result:
            if isinstance(result[key], np.ndarray):
                if result[key].size == 0:
                    result[key] = None
                else:
                    result[key] = result[key].tolist()
        return result

    def feature_array_names(self) -> List[str]:
        """Return names of all grid-based feature arrays (shape: grid_shape)."""
        return [
            "ensemble_mean",
            "ensemble_median",
            "ensemble_min",
            "ensemble_max",
            "ensemble_std",
            "ensemble_range",
            "ensemble_iqr",
            "ensemble_p10",
            "ensemble_p25",
            "ensemble_p75",
            "ensemble_p90",
            "coefficient_of_variation",
            "ensemble_skewness",
            "probability_rain_gt_1mm",
            "probability_rain_gt_10mm",
            "probability_rain_gt_25mm",
            "probability_rain_gt_50mm",
            "probability_rain_gt_100mm",
            "gradient_magnitude",
            "latitude_gradient",
            "longitude_gradient",
            "mean_pairwise_member_difference",
            "maximum_ensemble_gap",
            "member_agreement_fraction",
        ]


def extract_ensemble_rainfall_features(
    ensemble_members: Dict[int, Tuple[np.ndarray, Dict[str, Any]]],
    grid_metadata: Dict[str, Any],
    extraction_timestamp: Optional[datetime] = None,
) -> EnsembleRainfallFeatures:
    """Extract ensemble rainfall features from TP fields.

    Parameters
    ----------
    ensemble_members : Dict[int, Tuple[np.ndarray, Dict[str, Any]]]
        Dictionary mapping member_id (int) to (values_1d, metadata_dict).
        - values_1d: 1D numpy array of TP values (will be reshaped to grid)
        - metadata_dict: GRIB message metadata dict with at least:
          - data_date, data_time, step, step_type, forecast_type, short_name
          - number_of_values, grid dimensions (ni, nj)
          - grid location and spacing (first_lat, first_lon, last_lat, last_lon,
            i_increment, j_increment)
        Members will be sorted by ID to ensure consistent ordering.

    grid_metadata : Dict[str, Any]
        Consolidated grid metadata (shape, location, spacing) that should be
        consistent across all ensemble members.

    extraction_timestamp : Optional[datetime], optional
        UTC datetime to record when features were extracted. If None, uses current UTC time.

    Returns
    -------
    EnsembleRainfallFeatures
        Complete feature set for the ensemble forecast.

    Raises
    ------
    ValueError
        If ensemble_members is empty, or if metadata is inconsistent.
    """
    if not ensemble_members:
        raise ValueError("ensemble_members cannot be empty")

    if extraction_timestamp is None:
        from datetime import timezone

        extraction_timestamp = datetime.now(timezone.utc)

    # Sort members by ID for consistent ordering
    sorted_member_ids = sorted(ensemble_members.keys())
    n_members = len(sorted_member_ids)

    # Extract first metadata to get dimensions and forecast info
    first_member_id = sorted_member_ids[0]
    first_values, first_meta = ensemble_members[first_member_id]

    # Grid dimensions
    ni = grid_metadata.get("ni") or first_meta.get("ni")
    nj = grid_metadata.get("nj") or first_meta.get("nj")
    if not ni or not nj:
        raise ValueError("Grid dimensions (ni, nj) not found in metadata")

    grid_shape = (nj, ni)  # (latitude, longitude)
    n_points = ni * nj

    # Forecast metadata
    forecast_date = first_meta.get("data_date", 0)
    forecast_time = first_meta.get("data_time", 0)
    forecast_step = first_meta.get("step", 0)
    forecast_step_type = first_meta.get("step_type", "unknown")

    # Initialize time
    initialization_time = _parse_initialization_time(forecast_date, forecast_time)

    # Grid metadata
    first_lat = grid_metadata.get("first_lat") or first_meta.get("first_lat")
    first_lon = grid_metadata.get("first_lon") or first_meta.get("first_lon")
    last_lat = grid_metadata.get("last_lat") or first_meta.get("last_lat")
    last_lon = grid_metadata.get("last_lon") or first_meta.get("last_lon")
    lat_increment = grid_metadata.get("lat_increment") or first_meta.get("j_increment")
    lon_increment = grid_metadata.get("lon_increment") or first_meta.get("i_increment")

    # Build 3D array: (n_members, nj, ni)
    ensemble_3d = np.full((n_members, nj, ni), np.nan, dtype=np.float64)

    for idx, member_id in enumerate(sorted_member_ids):
        values_1d, meta = ensemble_members[member_id]
        values_1d = np.asarray(values_1d, dtype=np.float64)

        if values_1d.size != n_points:
            raise ValueError(
                f"Member {member_id}: expected {n_points} points, got {values_1d.size}"
            )

        ensemble_3d[idx, :, :] = values_1d.reshape(grid_shape)

    # Count valid members at any grid point
    valid_members = np.sum(~np.isnan(ensemble_3d), axis=0) > 0
    valid_member_count = int(np.sum(valid_members))

    # =========================================================================
    # Central Statistics
    # =========================================================================

    ensemble_mean = np.nanmean(ensemble_3d, axis=0)
    ensemble_median = np.nanmedian(ensemble_3d, axis=0)
    ensemble_min = np.nanmin(ensemble_3d, axis=0)
    ensemble_max = np.nanmax(ensemble_3d, axis=0)

    # Handle all-NaN cells
    ensemble_mean[~valid_members] = np.nan
    ensemble_median[~valid_members] = np.nan
    ensemble_min[~valid_members] = np.nan
    ensemble_max[~valid_members] = np.nan

    # =========================================================================
    # Spread Statistics
    # =========================================================================

    ensemble_std = np.nanstd(ensemble_3d, axis=0, ddof=1)  # Sample std
    ensemble_range = ensemble_max - ensemble_min
    ensemble_iqr = np.nanpercentile(ensemble_3d, 75, axis=0) - np.nanpercentile(
        ensemble_3d, 25, axis=0
    )

    ensemble_std[~valid_members] = np.nan
    ensemble_range[~valid_members] = np.nan
    ensemble_iqr[~valid_members] = np.nan

    # =========================================================================
    # Percentiles
    # =========================================================================

    ensemble_p10 = np.nanpercentile(ensemble_3d, 10, axis=0)
    ensemble_p25 = np.nanpercentile(ensemble_3d, 25, axis=0)
    ensemble_p75 = np.nanpercentile(ensemble_3d, 75, axis=0)
    ensemble_p90 = np.nanpercentile(ensemble_3d, 90, axis=0)

    ensemble_p10[~valid_members] = np.nan
    ensemble_p25[~valid_members] = np.nan
    ensemble_p75[~valid_members] = np.nan
    ensemble_p90[~valid_members] = np.nan

    # =========================================================================
    # Shape Descriptors
    # =========================================================================

    # Coefficient of variation: std / mean
    # Handle zero mean by using a safe threshold
    coefficient_of_variation = np.full_like(ensemble_std, np.nan, dtype=np.float64)
    safe_mean = ensemble_mean.copy()
    nonzero_mask = (np.abs(safe_mean) > 1e-10) & valid_members
    coefficient_of_variation[nonzero_mask] = ensemble_std[nonzero_mask] / safe_mean[nonzero_mask]

    # Skewness: (mean of (x - mean)^3) / std^3
    # Only compute where variance is non-trivial
    ensemble_skewness = np.full_like(ensemble_std, np.nan, dtype=np.float64)
    safe_std = ensemble_std.copy()
    safe_std[safe_std < 1e-10] = np.nan
    nonzero_std = ~np.isnan(safe_std) & valid_members

    if np.any(nonzero_std):
        centered_3d = ensemble_3d - ensemble_mean[np.newaxis, :, :]
        third_moment = np.nanmean(centered_3d**3, axis=0)
        ensemble_skewness[nonzero_std] = third_moment[nonzero_std] / (safe_std[nonzero_std] ** 3)

    # =========================================================================
    # Event Probability Features
    # =========================================================================

    def _probability_above_threshold(ensemble_3d_: np.ndarray, threshold: float) -> np.ndarray:
        """Count fraction of members above threshold, ignoring NaNs."""
        above = ensemble_3d_ > threshold
        n_valid = np.sum(~np.isnan(ensemble_3d_), axis=0)
        n_above = np.sum(above, axis=0)
        result = np.full_like(ensemble_mean, np.nan)
        valid = n_valid > 0
        result[valid] = n_above[valid].astype(np.float64) / n_valid[valid].astype(np.float64)
        return result

    probability_rain_gt_1mm = _probability_above_threshold(ensemble_3d, 1.0)
    probability_rain_gt_10mm = _probability_above_threshold(ensemble_3d, 10.0)
    probability_rain_gt_25mm = _probability_above_threshold(ensemble_3d, 25.0)
    probability_rain_gt_50mm = _probability_above_threshold(ensemble_3d, 50.0)
    probability_rain_gt_100mm = _probability_above_threshold(ensemble_3d, 100.0)

    # =========================================================================
    # Spatial Features (on ensemble_mean)
    # =========================================================================

    latitude_gradient, longitude_gradient = _compute_spatial_gradients(ensemble_mean)
    gradient_magnitude = np.sqrt(latitude_gradient**2 + longitude_gradient**2)

    # =========================================================================
    # Ensemble Geometry Features
    # =========================================================================

    # Mean pairwise member difference
    mean_pairwise_diff = _compute_mean_pairwise_difference(ensemble_3d)

    # Maximum gap in sorted ensemble members (measures clustering/bimodality)
    max_gap = _compute_maximum_ensemble_gap(ensemble_3d)

    # Member agreement fraction
    member_agreement = _compute_member_agreement_fraction(ensemble_3d, ensemble_mean)

    # =========================================================================
    # Build result object
    # =========================================================================

    feature_names = [
        "ensemble_mean",
        "ensemble_median",
        "ensemble_min",
        "ensemble_max",
        "ensemble_std",
        "ensemble_range",
        "ensemble_iqr",
        "ensemble_p10",
        "ensemble_p25",
        "ensemble_p75",
        "ensemble_p90",
        "coefficient_of_variation",
        "ensemble_skewness",
        "probability_rain_gt_1mm",
        "probability_rain_gt_10mm",
        "probability_rain_gt_25mm",
        "probability_rain_gt_50mm",
        "probability_rain_gt_100mm",
        "gradient_magnitude",
        "latitude_gradient",
        "longitude_gradient",
        "mean_pairwise_member_difference",
        "maximum_ensemble_gap",
        "member_agreement_fraction",
    ]

    return EnsembleRainfallFeatures(
        forecast_date=forecast_date,
        forecast_time=forecast_time,
        forecast_step=forecast_step,
        forecast_step_type=forecast_step_type,
        initialization_time=initialization_time,
        member_count=n_members,
        valid_member_count=valid_member_count,
        grid_shape=grid_shape,
        grid_first_lat=first_lat,
        grid_first_lon=first_lon,
        grid_last_lat=last_lat,
        grid_last_lon=last_lon,
        grid_lat_increment=lat_increment,
        grid_lon_increment=lon_increment,
        ensemble_mean=ensemble_mean,
        ensemble_median=ensemble_median,
        ensemble_min=ensemble_min,
        ensemble_max=ensemble_max,
        ensemble_std=ensemble_std,
        ensemble_range=ensemble_range,
        ensemble_iqr=ensemble_iqr,
        ensemble_p10=ensemble_p10,
        ensemble_p25=ensemble_p25,
        ensemble_p75=ensemble_p75,
        ensemble_p90=ensemble_p90,
        coefficient_of_variation=coefficient_of_variation,
        ensemble_skewness=ensemble_skewness,
        probability_rain_gt_1mm=probability_rain_gt_1mm,
        probability_rain_gt_10mm=probability_rain_gt_10mm,
        probability_rain_gt_25mm=probability_rain_gt_25mm,
        probability_rain_gt_50mm=probability_rain_gt_50mm,
        probability_rain_gt_100mm=probability_rain_gt_100mm,
        gradient_magnitude=gradient_magnitude,
        latitude_gradient=latitude_gradient,
        longitude_gradient=longitude_gradient,
        mean_pairwise_member_difference=mean_pairwise_diff,
        maximum_ensemble_gap=max_gap,
        member_agreement_fraction=member_agreement,
        feature_names=feature_names,
        source_metadata=first_meta,
        extraction_timestamp=extraction_timestamp,
    )


# ============================================================================
# Helper Functions
# ============================================================================


def _parse_initialization_time(data_date: int, data_time: int) -> Optional[datetime]:
    """Convert GRIB date/time to aware UTC datetime.

    Parameters
    ----------
    data_date : int
        YYYYMMDD format
    data_time : int
        HHMM format as integer

    Returns
    -------
    Optional[datetime]
        UTC-aware datetime, or None if metadata is invalid.
    """
    if data_date <= 0 or not 0 <= data_time <= 2359:
        return None

    hour, minute = divmod(data_time, 100)
    if minute > 59:
        return None

    try:
        from datetime import timezone

        return datetime(
            data_date // 10000,
            (data_date // 100) % 100,
            data_date % 100,
            hour,
            minute,
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None


def _compute_spatial_gradients(
    field: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute spatial gradients of ensemble mean on regular lat/lon grid.

    Gradients are computed in grid space (not distance normalized).

    Parameters
    ----------
    field : np.ndarray
        2D field (shape: nj, ni). Index [0, :] is northernmost latitude,
        index [:, 0] is westernmost longitude.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        (latitude_gradient, longitude_gradient), each same shape as field.
        Edges use one-sided differences. NaN where gradient undefined.
    """
    nj, ni = field.shape
    lat_grad = np.full_like(field, np.nan, dtype=np.float64)
    lon_grad = np.full_like(field, np.nan, dtype=np.float64)

    # Interior points: central differences
    if nj > 2:
        lat_grad[1:-1, :] = (field[2:, :] - field[:-2, :]) / 2.0

    if ni > 2:
        lon_grad[:, 1:-1] = (field[:, 2:] - field[:, :-2]) / 2.0

    # Edges: one-sided differences
    if nj > 1:
        lat_grad[0, :] = field[1, :] - field[0, :]  # Forward diff at top
        lat_grad[-1, :] = field[-1, :] - field[-2, :]  # Backward diff at bottom

    if ni > 1:
        lon_grad[:, 0] = field[:, 1] - field[:, 0]  # Forward diff at left
        lon_grad[:, -1] = field[:, -1] - field[:, -2]  # Backward diff at right

    return lat_grad, lon_grad


def _compute_mean_pairwise_difference(ensemble_3d: np.ndarray) -> np.ndarray:
    """Compute mean absolute pairwise difference among ensemble members.

    At each grid cell, computes the mean of |m_i - m_j| over all distinct pairs.
    Ignores NaN members.

    Parameters
    ----------
    ensemble_3d : np.ndarray
        Shape (n_members, nj, ni). NaN values represent invalid ensemble members.

    Returns
    -------
    np.ndarray
        Shape (nj, ni). Mean pairwise difference at each grid point.
    """
    n_members, nj, ni = ensemble_3d.shape
    result = np.full((nj, ni), np.nan, dtype=np.float64)

    # For each grid point, compute pairwise differences
    for i in range(nj):
        for j in range(ni):
            members = ensemble_3d[:, i, j]
            valid = members[~np.isnan(members)]

            if len(valid) > 1:
                # All pairwise differences
                pairwise_diffs = []
                for k1 in range(len(valid)):
                    for k2 in range(k1 + 1, len(valid)):
                        pairwise_diffs.append(np.abs(valid[k1] - valid[k2]))

                result[i, j] = np.mean(pairwise_diffs) if pairwise_diffs else np.nan

    return result


def _compute_maximum_ensemble_gap(ensemble_3d: np.ndarray) -> np.ndarray:
    """Compute maximum gap between adjacent sorted ensemble members.

    For each grid point, sorts valid ensemble members and finds the largest
    gap between adjacent members. A large gap indicates ensemble clustering
    or bimodality. A small gap indicates ensemble consensus.

    Parameters
    ----------
    ensemble_3d : np.ndarray
        Shape (n_members, nj, ni). NaN values ignored.

    Returns
    -------
    np.ndarray
        Shape (nj, ni). Maximum gap, or NaN if fewer than 2 valid members.
    """
    n_members, nj, ni = ensemble_3d.shape
    result = np.full((nj, ni), np.nan, dtype=np.float64)

    for i in range(nj):
        for j in range(ni):
            members = ensemble_3d[:, i, j]
            valid = members[~np.isnan(members)]

            if len(valid) > 1:
                sorted_members = np.sort(valid)
                gaps = np.diff(sorted_members)
                result[i, j] = np.max(gaps)

    return result


def _compute_member_agreement_fraction(
    ensemble_3d: np.ndarray, mean_field: np.ndarray
) -> np.ndarray:
    """Compute fraction of member pairs within 25% of the ensemble mean.

    Agreement is defined as |m_i - m_j| < 0.25 * mean_field.
    At zero-rainfall cells (mean < 1e-3 mm), uses absolute threshold 0.01 mm.

    Parameters
    ----------
    ensemble_3d : np.ndarray
        Shape (n_members, nj, ni).
    mean_field : np.ndarray
        Shape (nj, ni). Ensemble mean at each grid point.

    Returns
    -------
    np.ndarray
        Shape (nj, ni). Fraction of member pairs in agreement, or NaN if undefined.
    """
    n_members, nj, ni = ensemble_3d.shape
    result = np.full((nj, ni), np.nan, dtype=np.float64)

    for i in range(nj):
        for j in range(ni):
            members = ensemble_3d[:, i, j]
            valid = members[~np.isnan(members)]

            if len(valid) > 1:
                mean_val = mean_field[i, j]

                # Determine threshold
                if np.isnan(mean_val) or mean_val < 1e-3:
                    threshold = 0.01  # Absolute threshold for dry cells
                else:
                    threshold = 0.25 * mean_val

                # Count pairs in agreement
                n_pairs = 0
                n_agree = 0
                for k1 in range(len(valid)):
                    for k2 in range(k1 + 1, len(valid)):
                        n_pairs += 1
                        if np.abs(valid[k1] - valid[k2]) < threshold:
                            n_agree += 1

                if n_pairs > 0:
                    result[i, j] = n_agree / n_pairs

    return result
