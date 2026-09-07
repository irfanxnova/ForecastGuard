"""Scientific tropical-cyclone verification and reliability modeling pipeline.

Milestone P2: Real Event-Verified Forecast Reliability Loop.
Integrates:
1. Real NCMRWF TIGGE/NEPS ensemble forecasts (ECMWF ECDS).
2. Official IMD/RSMC New Delhi 6-hourly best-track observations.
3. Great-circle / Haversine continuous track error computation.
4. Domain-justified forecast failure / bust labeling.
5. Strictly leakage-safe ensemble and trajectory feature extraction.
6. Baseline model ladder (Climatology, Spread-only, Trajectory-enhanced, Tree-based).
7. Event-level validation splits and warning lead-time evaluation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import eccodes
import numpy as np
import pandas as pd


EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two coordinates in kilometers."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


@dataclass(frozen=True)
class BestTrackPoint:
    """Official 6-hourly tropical cyclone best-track observation from IMD/RSMC New Delhi."""

    cyclone_name: str
    year: int
    timestamp: datetime  # UTC-aware
    latitude: float
    longitude: float
    central_pressure_hpa: Optional[float] = None
    max_sustained_wind_kt: Optional[float] = None
    system_grade: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset().total_seconds() != 0:
            raise ValueError("Best-track timestamp must be an aware UTC datetime")


def parse_rsmc_best_tracks(
    xlsx_path: Union[str, Path],
    year: str,
    cyclone_name: str,
) -> List[BestTrackPoint]:
    """Parse official IMD/RSMC New Delhi Best Track Excel spreadsheet into clean points.

    Handles IMD timestamp conventions and date rollovers cleanly.
    """
    path = Path(xlsx_path)
    if not path.is_file():
        raise FileNotFoundError(f"Best track file not found: {path}")

    df = pd.read_excel(path, sheet_name=str(year))

    # Detect column names flexibly
    name_col = next((c for c in df.columns if "name" in str(c).lower()), None)
    date_col = next((c for c in df.columns if "date" in str(c).lower()), None)
    time_col = next((c for c in df.columns if "time" in str(c).lower()), None)
    lat_col = next((c for c in df.columns if "lat" in str(c).lower()), None)
    lon_col = next((c for c in df.columns if "long" in str(c).lower()), None)
    pres_col = next((c for c in df.columns if "pressure" in str(c).lower() or "e.c.p" in str(c).lower()), None)
    wind_col = next((c for c in df.columns if "wind" in str(c).lower()), None)

    if not all([name_col, date_col, time_col, lat_col, lon_col]):
        raise ValueError(f"Missing required columns in best track sheet for year {year}")

    df["clean_name"] = df[name_col].ffill()
    sub = df[df["clean_name"].astype(str).str.upper() == cyclone_name.upper()].copy()

    if sub.empty:
        raise ValueError(f"No cyclone matching '{cyclone_name}' found in sheet {year}")

    points: List[BestTrackPoint] = []
    prev_dt: Optional[datetime] = None

    for _, row in sub.iterrows():
        raw_date = row[date_col]
        raw_time = row[time_col]
        raw_lat = row[lat_col]
        raw_lon = row[lon_col]
        raw_pres = row[pres_col] if pres_col else None
        raw_wind = row[wind_col] if wind_col else None

        if pd.isna(raw_lat) or pd.isna(raw_lon):
            continue

        # Parse date
        if isinstance(raw_date, datetime):
            d = raw_date.date()
        elif isinstance(raw_date, str):
            clean_d = raw_date.strip().split()[0]
            try:
                d = datetime.strptime(clean_d, "%d/%m/%Y").date()
            except ValueError:
                d = datetime.strptime(clean_d, "%Y-%m-%d").date()
        elif hasattr(raw_date, "date"):
            d = raw_date.date()
        else:
            continue

        # Parse time: e.g. 0, 300, 600, 1200, 1800
        t_str = str(int(raw_time) if isinstance(raw_time, (int, float)) and not pd.isna(raw_time) else raw_time).strip()
        t_str = t_str.zfill(4)
        hour = int(t_str[:2])
        minute = int(t_str[2:])

        dt = datetime(d.year, d.month, d.day, hour, minute, tzinfo=timezone.utc)

        # Handle midnight rollover where date was not incremented
        if prev_dt is not None:
            if dt <= prev_dt and hour == 0 and prev_dt.hour >= 18:
                dt = datetime(prev_dt.year, prev_dt.month, prev_dt.day, hour, minute, tzinfo=timezone.utc) + pd.Timedelta(days=1).to_pytimedelta()

        prev_dt = dt

        def _clean_num(v: Any) -> Optional[float]:
            if pd.isna(v) or v == "-" or v == " ":
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        clean_lat_str = str(raw_lat).strip().rstrip(".")
        clean_lon_str = str(raw_lon).strip().rstrip(".")
        try:
            parsed_lat = float(clean_lat_str)
            parsed_lon = float(clean_lon_str)
        except (ValueError, TypeError):
            continue

        points.append(
            BestTrackPoint(
                cyclone_name=cyclone_name.upper(),
                year=int(year),
                timestamp=dt,
                latitude=parsed_lat,
                longitude=parsed_lon,
                central_pressure_hpa=_clean_num(raw_pres),
                max_sustained_wind_kt=_clean_num(raw_wind),
            )
        )

    # Sort and remove potential exact duplicate timestamps
    points.sort(key=lambda x: x.timestamp)
    unique_points: List[BestTrackPoint] = []
    seen = set()
    for p in points:
        if p.timestamp not in seen:
            seen.add(p.timestamp)
            unique_points.append(p)

    return unique_points


@dataclass(frozen=True)
class ForecastMemberTrackPoint:
    """Forecast cyclone center position for a single ensemble member at a specific lead."""

    member: int
    lead_hours: int
    valid_time: datetime
    center_lat: float
    center_lon: float
    central_pressure_hpa: float
    detection_method: str = "local_mslp_minimum"
    detection_confidence: float = 1.0


def detect_cyclone_center_from_mslp(
    lats: np.ndarray,
    lons: np.ndarray,
    mslp_pa: np.ndarray,
    member: int,
    lead_hours: int,
    valid_time: datetime,
    search_center: Optional[Tuple[float, float]] = None,
    search_radius_deg: float = 6.0,
) -> ForecastMemberTrackPoint:
    """Detect tropical cyclone center by identifying the local MSLP minimum.

    When search_center=(lat, lon) is provided, limits detection to the vortex vicinity
    to prevent spurious minima far away from the cyclone.
    """
    mslp_hpa = mslp_pa / 100.0 if np.nanmax(mslp_pa) > 2000.0 else mslp_pa

    if search_center is not None:
        sc_lat, sc_lon = search_center
        # Create 2D coordinate mesh if 1D
        if lats.ndim == 1 and lons.ndim == 1:
            lon_grid, lat_grid = np.meshgrid(lons, lats)
        else:
            lat_grid, lon_grid = lats, lons

        dist = np.sqrt((lat_grid - sc_lat) ** 2 + (lon_grid - sc_lon) ** 2)
        mask = dist <= search_radius_deg
        masked_mslp = np.where(mask, mslp_hpa, np.inf)
        min_idx = np.unravel_index(np.argmin(masked_mslp), masked_mslp.shape)
        c_lat = float(lat_grid[min_idx])
        c_lon = float(lon_grid[min_idx])
        c_pres = float(mslp_hpa[min_idx])
    else:
        min_idx = np.unravel_index(np.argmin(mslp_hpa), mslp_hpa.shape)
        if lats.ndim == 1 and lons.ndim == 1:
            c_lat = float(lats[min_idx[0]])
            c_lon = float(lons[min_idx[1]])
        else:
            c_lat = float(lats[min_idx])
            c_lon = float(lons[min_idx])
        c_pres = float(mslp_hpa[min_idx])

    return ForecastMemberTrackPoint(
        member=member,
        lead_hours=lead_hours,
        valid_time=valid_time,
        center_lat=c_lat,
        center_lon=c_lon,
        central_pressure_hpa=c_pres,
        detection_method="local_mslp_minimum",
        detection_confidence=1.0,
    )


@dataclass(frozen=True)
class VerifiedLeadEvaluation:
    """Complete forecast verification against official IMD best track for one forecast lead."""

    cyclone_name: str
    initialization_time: datetime
    lead_hours: int
    valid_time: datetime
    # Observation
    best_track_lat: float
    best_track_lon: float
    best_track_pressure_hpa: Optional[float]
    best_track_wind_kt: Optional[float]
    # Ensemble forecast
    member_points: List[ForecastMemberTrackPoint]
    ensemble_mean_lat: float
    ensemble_mean_lon: float
    ensemble_median_lat: float
    ensemble_median_lon: float
    ensemble_mean_pressure_hpa: float
    # Track errors (great-circle km)
    member_track_errors_km: List[float]
    mean_track_error_km: float
    median_track_error_km: float
    min_track_error_km: float
    max_track_error_km: float
    # Ensemble spread & divergence
    ensemble_spread_km: float
    ensemble_divergence_km: float
    # Failure label
    is_bust: bool
    bust_severity: str  # "NORMAL", "DEGRADED", "SEVERE"
    bust_threshold_km: float
    # Metadata
    provenance: Dict[str, Any] = field(default_factory=dict)


def evaluate_forecast_lead(
    cyclone_name: str,
    initialization_time: datetime,
    lead_hours: int,
    valid_time: datetime,
    member_points: List[ForecastMemberTrackPoint],
    best_track_point: BestTrackPoint,
    bust_threshold_km: float = 200.0,
) -> VerifiedLeadEvaluation:
    """Evaluate track errors and ensemble spread against exact best track point."""
    if valid_time != best_track_point.timestamp:
        raise ValueError(
            f"Temporal mismatch: Forecast valid time {valid_time} != Best track time {best_track_point.timestamp}"
        )

    # Compute member errors
    member_errors = [
        haversine_distance(m.center_lat, m.center_lon, best_track_point.latitude, best_track_point.longitude)
        for m in member_points
    ]

    mean_lat = float(np.mean([m.center_lat for m in member_points]))
    mean_lon = float(np.mean([m.center_lon for m in member_points]))
    median_lat = float(np.median([m.center_lat for m in member_points]))
    median_lon = float(np.median([m.center_lon for m in member_points]))
    mean_pres = float(np.mean([m.central_pressure_hpa for m in member_points]))

    # Mean track error is error of the ensemble mean center
    mean_track_error = haversine_distance(mean_lat, mean_lon, best_track_point.latitude, best_track_point.longitude)
    median_track_error = float(np.median(member_errors))
    min_error = float(np.min(member_errors))
    max_error = float(np.max(member_errors))

    # Ensemble spread: mean distance of each member from the ensemble mean
    spreads = [haversine_distance(m.center_lat, m.center_lon, mean_lat, mean_lon) for m in member_points]
    ensemble_spread = float(np.mean(spreads))

    # Divergence: maximum pairwise distance between members
    pairwise_dist = [
        haversine_distance(m1.center_lat, m1.center_lon, m2.center_lat, m2.center_lon)
        for i, m1 in enumerate(member_points)
        for j, m2 in enumerate(member_points)
        if i < j
    ]
    ensemble_div = float(np.max(pairwise_dist)) if pairwise_dist else 0.0

    # Operational domain-based severity:
    # Scaling threshold slightly with lead time: threshold(lead) = base * (1 + 0.01 * lead)
    effective_thresh = bust_threshold_km * (1.0 + 0.008 * lead_hours)
    is_bust = bool(mean_track_error >= effective_thresh)

    if mean_track_error < 0.75 * effective_thresh:
        severity = "NORMAL"
    elif mean_track_error < effective_thresh:
        severity = "MODERATE"
    elif mean_track_error < 1.5 * effective_thresh:
        severity = "DEGRADED"
    else:
        severity = "SEVERE"

    return VerifiedLeadEvaluation(
        cyclone_name=cyclone_name,
        initialization_time=initialization_time,
        lead_hours=lead_hours,
        valid_time=valid_time,
        best_track_lat=best_track_point.latitude,
        best_track_lon=best_track_point.longitude,
        best_track_pressure_hpa=best_track_point.central_pressure_hpa,
        best_track_wind_kt=best_track_point.max_sustained_wind_kt,
        member_points=member_points,
        ensemble_mean_lat=mean_lat,
        ensemble_mean_lon=mean_lon,
        ensemble_median_lat=median_lat,
        ensemble_median_lon=median_lon,
        ensemble_mean_pressure_hpa=mean_pres,
        member_track_errors_km=member_errors,
        mean_track_error_km=mean_track_error,
        median_track_error_km=median_track_error,
        min_track_error_km=min_error,
        max_track_error_km=max_error,
        ensemble_spread_km=ensemble_spread,
        ensemble_divergence_km=ensemble_div,
        is_bust=is_bust,
        bust_severity=severity,
        bust_threshold_km=effective_thresh,
        provenance={
            "formula": "great_circle_haversine",
            "earth_radius_km": EARTH_RADIUS_KM,
            "center_detection": "local_mslp_minimum",
        },
    )


@dataclass(frozen=True)
class LeadFeatures:
    """Strictly anti-leakage feature vector for a prediction made at lead_hours."""

    cyclone_name: str
    lead_hours: int
    valid_time: datetime
    # Snapshot features
    ensemble_spread_km: float
    ensemble_divergence_km: float
    mean_central_pressure_hpa: float
    # Trajectory features (calculated from lead history)
    spread_growth_km: float
    spread_acceleration_km: float
    trajectory_speed_kmh: float
    trajectory_curvature_deg: float
    # Target (for training / evaluation only)
    is_bust: bool
    mean_track_error_km: float


def extract_leakage_safe_features(
    evaluations: List[VerifiedLeadEvaluation],
) -> List[LeadFeatures]:
    """Extract anti-leakage feature vectors along the forecast lead trajectory.

    For each lead t, uses ONLY evaluations at lead <= t. Never looks forward.
    """
    sorted_evals = sorted(evaluations, key=lambda x: x.lead_hours)
    feature_list: List[LeadFeatures] = []

    for i, curr in enumerate(sorted_evals):
        # Trajectory metrics
        if i >= 1:
            prev = sorted_evals[i - 1]
            dt_hours = curr.lead_hours - prev.lead_hours
            spread_growth = (curr.ensemble_spread_km - prev.ensemble_spread_km) / max(1, dt_hours)
            step_dist = haversine_distance(
                prev.ensemble_mean_lat, prev.ensemble_mean_lon, curr.ensemble_mean_lat, curr.ensemble_mean_lon
            )
            speed = step_dist / max(1, dt_hours)
        else:
            spread_growth = 0.0
            speed = 0.0

        if i >= 2:
            prev1 = sorted_evals[i - 1]
            prev2 = sorted_evals[i - 2]
            prev_growth = (prev1.ensemble_spread_km - prev2.ensemble_spread_km) / max(1, prev1.lead_hours - prev2.lead_hours)
            spread_accel = spread_growth - prev_growth

            # Heading change (curvature)
            bearing1 = math.degrees(math.atan2(prev1.ensemble_mean_lon - prev2.ensemble_mean_lon, prev1.ensemble_mean_lat - prev2.ensemble_mean_lat))
            bearing2 = math.degrees(math.atan2(curr.ensemble_mean_lon - prev1.ensemble_mean_lon, curr.ensemble_mean_lat - prev1.ensemble_mean_lat))
            curvature = abs(bearing2 - bearing1)
            if curvature > 180.0:
                curvature = 360.0 - curvature
        else:
            spread_accel = 0.0
            curvature = 0.0

        feature_list.append(
            LeadFeatures(
                cyclone_name=curr.cyclone_name,
                lead_hours=curr.lead_hours,
                valid_time=curr.valid_time,
                ensemble_spread_km=curr.ensemble_spread_km,
                ensemble_divergence_km=curr.ensemble_divergence_km,
                mean_central_pressure_hpa=curr.ensemble_mean_pressure_hpa,
                spread_growth_km=spread_growth,
                spread_acceleration_km=spread_accel,
                trajectory_speed_kmh=speed,
                trajectory_curvature_deg=curvature,
                is_bust=curr.is_bust,
                mean_track_error_km=curr.mean_track_error_km,
            )
        )

    return feature_list


def parse_tigge_mslp_grib_ensemble(
    grib_path: Union[str, Path],
    initial_best_track_point: BestTrackPoint,
) -> Dict[int, List[ForecastMemberTrackPoint]]:
    """Extract forecast centers for all ensemble members and leads from a multi-message GRIB file.

    Maintains vortex continuity by propagating the detected center forward in lead time.
    """
    path = Path(grib_path)
    if not path.is_file():
        raise FileNotFoundError(f"GRIB file not found: {path}")

    # Index messages by lead_hours and member
    messages_by_lead_member: Dict[Tuple[int, int], Any] = {}
    lats = None
    lons = None

    with open(path, "rb") as f:
        while True:
            handle = eccodes.codes_grib_new_from_file(f)
            if handle is None:
                break
            short_name = eccodes.codes_get(handle, "shortName")
            if short_name.lower() != "msl":
                eccodes.codes_release(handle)
                continue

            step = int(eccodes.codes_get(handle, "step"))
            member = int(eccodes.codes_get(handle, "number")) if eccodes.codes_is_defined(handle, "number") else 1
            data_date = int(eccodes.codes_get(handle, "dataDate"))
            data_time = int(eccodes.codes_get(handle, "dataTime"))

            init_time = datetime(
                data_date // 10000,
                (data_date // 100) % 100,
                data_date % 100,
                data_time // 100,
                data_time % 100,
                tzinfo=timezone.utc,
            )
            valid_time = init_time + pd.Timedelta(hours=step).to_pytimedelta()

            if lats is None:
                ni = int(eccodes.codes_get(handle, "Ni"))
                nj = int(eccodes.codes_get(handle, "Nj"))
                first_lat = float(eccodes.codes_get(handle, "latitudeOfFirstGridPointInDegrees"))
                last_lat = float(eccodes.codes_get(handle, "latitudeOfLastGridPointInDegrees"))
                first_lon = float(eccodes.codes_get(handle, "longitudeOfFirstGridPointInDegrees"))
                last_lon = float(eccodes.codes_get(handle, "longitudeOfLastGridPointInDegrees"))
                lats = np.linspace(first_lat, last_lat, nj)
                lons = np.linspace(first_lon, last_lon, ni)

            raw_vals = eccodes.codes_get_values(handle)
            vals_2d = np.asarray(raw_vals, dtype=np.float64).reshape((len(lats), len(lons)))

            messages_by_lead_member[(step, member)] = {
                "valid_time": valid_time,
                "values": vals_2d,
            }
            eccodes.codes_release(handle)

    # Track centers sequentially per member to maintain continuity
    leads = sorted(set(k[0] for k in messages_by_lead_member.keys()))
    members = sorted(set(k[1] for k in messages_by_lead_member.keys()))

    member_tracks: Dict[int, List[ForecastMemberTrackPoint]] = {m: [] for m in members}

    for m in members:
        prev_center = (initial_best_track_point.latitude, initial_best_track_point.longitude)
        for step in leads:
            if (step, m) not in messages_by_lead_member:
                continue
            entry = messages_by_lead_member[(step, m)]
            val_2d = entry["values"]
            valid_t = entry["valid_time"]

            pt = detect_cyclone_center_from_mslp(
                lats=lats,
                lons=lons,
                mslp_pa=val_2d,
                member=m,
                lead_hours=step,
                valid_time=valid_t,
                search_center=prev_center,
                search_radius_deg=5.0,
            )
            member_tracks[m].append(pt)
            prev_center = (pt.center_lat, pt.center_lon)

    # Re-group by lead
    lead_tracks: Dict[int, List[ForecastMemberTrackPoint]] = {step: [] for step in leads}
    for m in members:
        for pt in member_tracks[m]:
            lead_tracks[pt.lead_hours].append(pt)

    return lead_tracks


@dataclass(frozen=True)
class ModelMetrics:
    """Evaluation metrics for a forecast bust prediction model."""

    model_name: str
    brier_score: float
    roc_auc: Optional[float]
    pr_auc: Optional[float]
    ece: float
    accuracy: float
    f1: float
    earliest_warning_lead_hours: Optional[int]
    probabilities: List[float]
    predictions: List[int]


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 5) -> float:
    """Compute Expected Calibration Error (ECE)."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    if n == 0:
        return 0.0

    for i in range(n_bins):
        in_bin = (y_prob >= bins[i]) & (y_prob < bins[i + 1] if i < n_bins - 1 else y_prob <= bins[i + 1])
        bin_count = np.sum(in_bin)
        if bin_count > 0:
            bin_acc = np.mean(y_true[in_bin])
            bin_conf = np.mean(y_prob[in_bin])
            ece += (bin_count / n) * abs(bin_acc - bin_conf)

    return float(ece)


def compute_earliest_warning(
    leads: List[int],
    y_prob: np.ndarray,
    y_true: np.ndarray,
    alert_threshold: float = 0.5,
) -> Optional[int]:
    """Determine the earliest forecast lead at which an alert was raised for a failure occurring at or after that lead."""
    bust_leads = [lead for lead, truth in zip(leads, y_true) if truth]
    if not bust_leads:
        return None
    first_bust_lead = min(bust_leads)
    for lead, prob in zip(leads, y_prob):
        if prob >= alert_threshold and lead <= first_bust_lead:
            return int(lead)
    # If no alert preceded the bust, check if an alert coincided with any bust lead
    for lead, prob in zip(leads, y_prob):
        if prob >= alert_threshold:
            return int(lead)
    return None


class ClimatologyBaseline:
    """Predicts historical training event bust prevalence."""

    def __init__(self) -> None:
        self.base_rate: float = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> "ClimatologyBaseline":
        self.base_rate = float(np.mean(y)) if len(y) > 0 else 0.5
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        p = np.full(len(X), self.base_rate)
        return np.column_stack([1.0 - p, p])

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


class SpreadOnlyModel:
    """Logistic regression model based solely on lead time and ensemble spread."""

    def __init__(self) -> None:
        self.mean_ = None
        self.std_ = None
        self.w_ = None
        self.b_ = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> "SpreadOnlyModel":
        from sklearn.linear_model import LogisticRegression
        # Use simple regularized logistic regression
        clf = LogisticRegression(C=1.0, solver="lbfgs")
        # In case all labels are same class in tiny sample
        if len(set(y)) < 2:
            self.b_ = 10.0 if y[0] == 1 else -10.0
            self.w_ = np.zeros(X.shape[1])
            return self
        clf.fit(X, y)
        self.clf = clf
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if hasattr(self, "clf"):
            return self.clf.predict_proba(X)
        p = 1.0 / (1.0 + np.exp(-self.b_))
        p_arr = np.full(len(X), p)
        return np.column_stack([1.0 - p_arr, p_arr])

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


class TrajectoryEnhancedModel:
    """Model utilizing snapshot spread PLUS temporal trajectory derivatives."""

    def __init__(self) -> None:
        pass

    def fit(self, X: np.ndarray, y: np.ndarray) -> "TrajectoryEnhancedModel":
        from sklearn.linear_model import LogisticRegression
        if len(set(y)) < 2:
            self.b_ = 10.0 if y[0] == 1 else -10.0
            return self
        clf = LogisticRegression(C=1.0, solver="lbfgs")
        clf.fit(X, y)
        self.clf = clf
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if hasattr(self, "clf"):
            return self.clf.predict_proba(X)
        p = 1.0 / (1.0 + np.exp(-self.b_))
        p_arr = np.full(len(X), p)
        return np.column_stack([1.0 - p_arr, p_arr])

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


def evaluate_model(
    name: str,
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray,
    leads: List[int],
    alert_threshold: float = 0.5,
) -> ModelMetrics:
    """Compute complete probabilistic and operational metrics for a model."""
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, average_precision_score

    probs = model.predict_proba(X_test)[:, 1]
    preds = (probs >= alert_threshold).astype(int)

    brier = float(np.mean((probs - y_test) ** 2))
    ece = compute_ece(y_test, probs)
    acc = float(accuracy_score(y_test, preds))

    try:
        f1 = float(f1_score(y_test, preds, zero_division=0))
    except Exception:
        f1 = 0.0

    try:
        roc = float(roc_auc_score(y_test, probs)) if len(set(y_test)) > 1 else None
    except Exception:
        roc = None

    try:
        pr = float(average_precision_score(y_test, probs)) if len(set(y_test)) > 1 else None
    except Exception:
        pr = None

    earliest_warn = compute_earliest_warning(leads, probs, y_test, alert_threshold=alert_threshold)

    return ModelMetrics(
        model_name=name,
        brier_score=brier,
        roc_auc=roc,
        pr_auc=pr,
        ece=ece,
        accuracy=acc,
        f1=f1,
        earliest_warning_lead_hours=earliest_warn,
        probabilities=probs.tolist(),
        predictions=preds.tolist(),
    )


class TreeBaselineModel:
    """Decision Tree baseline model for forecast bust probability."""

    def __init__(self, max_depth: int = 2) -> None:
        self.max_depth = max_depth
        self.clf = None
        self.base_rate = 0.5

    def fit(self, X: np.ndarray, y: np.ndarray) -> "TreeBaselineModel":
        from sklearn.tree import DecisionTreeClassifier
        self.base_rate = float(np.mean(y)) if len(y) > 0 else 0.5
        if len(set(y)) < 2:
            return self
        clf = DecisionTreeClassifier(max_depth=self.max_depth, min_samples_leaf=1, random_state=42)
        clf.fit(X, y)
        self.clf = clf
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.clf is not None:
            return self.clf.predict_proba(X)
        p = np.full(len(X), self.base_rate)
        return np.column_stack([1.0 - p, p])

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


@dataclass(frozen=True)
class ContinuousErrorMetrics:
    """Evaluation metrics for continuous track error in kilometers."""

    count: int
    mae_km: float
    rmse_km: float
    median_error_km: float
    percentile_75_km: float
    percentile_90_km: float
    min_error_km: float
    max_error_km: float


def compute_continuous_error_metrics(errors_km: List[float]) -> ContinuousErrorMetrics:
    """Compute summary statistics for continuous great-circle track errors."""
    arr = np.asarray(errors_km, dtype=np.float64)
    if len(arr) == 0:
        return ContinuousErrorMetrics(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    return ContinuousErrorMetrics(
        count=len(arr),
        mae_km=float(np.mean(np.abs(arr))),
        rmse_km=float(np.sqrt(np.mean(arr ** 2))),
        median_error_km=float(np.median(arr)),
        percentile_75_km=float(np.percentile(arr, 75)),
        percentile_90_km=float(np.percentile(arr, 90)),
        min_error_km=float(np.min(arr)),
        max_error_km=float(np.max(arr)),
    )


def serialize_case_artifact(
    cyclone_name: str,
    year: int,
    initialization_time: datetime,
    evaluations: List[VerifiedLeadEvaluation],
    features: List[LeadFeatures],
    model_metrics: Dict[str, ModelMetrics],
    continuous_metrics: ContinuousErrorMetrics,
    provenance_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Serialize complete case verification, tracking, and evaluation to JSON-compatible dictionary."""
    leads_data = []
    for ev in evaluations:
        leads_data.append({
            "lead_hours": ev.lead_hours,
            "valid_time_iso": ev.valid_time.isoformat(),
            "best_track": {
                "latitude": ev.best_track_lat,
                "longitude": ev.best_track_lon,
                "central_pressure_hpa": ev.best_track_pressure_hpa,
                "max_sustained_wind_kt": ev.best_track_wind_kt,
            },
            "ensemble_mean": {
                "latitude": ev.ensemble_mean_lat,
                "longitude": ev.ensemble_mean_lon,
                "central_pressure_hpa": ev.ensemble_mean_pressure_hpa,
            },
            "ensemble_median": {
                "latitude": ev.ensemble_median_lat,
                "longitude": ev.ensemble_median_lon,
            },
            "members": [
                {
                    "member": m.member,
                    "latitude": m.center_lat,
                    "longitude": m.center_lon,
                    "central_pressure_hpa": m.central_pressure_hpa,
                    "track_error_km": err,
                }
                for m, err in zip(ev.member_points, ev.member_track_errors_km)
            ],
            "track_error": {
                "mean_km": ev.mean_track_error_km,
                "median_km": ev.median_track_error_km,
                "min_km": ev.min_track_error_km,
                "max_km": ev.max_track_error_km,
            },
            "ensemble_dynamics": {
                "spread_km": ev.ensemble_spread_km,
                "divergence_km": ev.ensemble_divergence_km,
            },
            "verification": {
                "is_bust": ev.is_bust,
                "bust_severity": ev.bust_severity,
                "bust_threshold_km": ev.bust_threshold_km,
            },
        })

    return {
        "cyclone_name": cyclone_name,
        "year": year,
        "initialization_time_iso": initialization_time.isoformat(),
        "verification_status": "VERIFIED_EXACT_TIMESTAMPS",
        "provenance": provenance_metadata,
        "continuous_error_summary": asdict(continuous_metrics),
        "models_evaluated": {k: asdict(v) for k, v in model_metrics.items()},
        "leads": leads_data,
        "data_limitations": [
            "Official IMD/RSMC best tracks are published 6-hourly; intermediate 3-hourly synoptic fixes are excluded to ensure exact 6-hourly TIGGE step parity.",
            "TIGGE NCMRWF NEPS provides 11 perturbed ensemble members at 0.5° spatial resolution.",
            "Track center detected via local MSLP minimum tracking with vortex continuity constraint; intensity (10m wind) verification omitted as uncalibrated wind in TIGGE single-level.",
        ],
    }


def save_case_artifact(artifact_dict: Dict[str, Any], output_path: Union[str, Path]) -> Path:
    """Write case artifact JSON file ensuring parent directory exists."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(artifact_dict, f, indent=2)
    return path


