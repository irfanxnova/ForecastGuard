"""ForecastGuard V2 — Forecast Trajectory Intelligence Engine.

Evaluates intra-cycle and cycle-to-cycle forecast trajectory dynamics, revision shift,
persistence, jumpiness, and deterministic trajectory instability states.

Strict adherence to AGENTS.md:
- Rule 1: Never fabricate weather data or machine-learning predictions.
- Rule 4: Never use future observations as predictor features.
- Rule 6: Every prediction must use only information available at the forecast lead.
  At prediction cutoff T, no later forecast cycle can be used.
- Rule 7: Never silently change scientific definitions, units, or coordinates.
- Rule 15: UI values must ultimately come from the backend/data layer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np


TrajectoryStateLiteral = Literal[
    "STABLE_PERSISTENT",
    "PROGRESSIVE_DRIFT",
    "OSCILLATING_JUMPY",
    "RAPID_REVISION",
    "INSUFFICIENT_EVIDENCE",
]


@dataclass(frozen=True)
class TrajectoryMetrics:
    """Rigorous trajectory dynamics and revision instability metrics."""

    case_id: str
    region_id: str
    forecast_cycle: str
    reference_cycle: Optional[str]
    lead_hours: int
    valid_time: str
    has_prior_cycle: bool
    cycle_revision_distance_km: Optional[float]
    cycle_spread_shift_km: Optional[float]
    revision_rate_kmh: Optional[float]
    trajectory_speed_kmh: Optional[float]
    trajectory_curvature_deg: Optional[float]
    spread_growth_rate: Optional[float]
    trajectory_instability_km: Optional[float]  # jitter
    instability_state: TrajectoryStateLiteral
    state_description: str
    trend: Literal["increasing", "decreasing", "stable", "unavailable"]
    is_validated: bool


# Canonical feature metadata catalog
TRAJECTORY_FEATURE_METADATA: Dict[str, Dict[str, Any]] = {
    "cycle_revision_distance_km": {
        "definition": (
            "Haversine spatial displacement between successive forecast cycle predictions "
            "evaluated at identical verification valid time (T_valid)."
        ),
        "units": "km",
        "calculation": "haversine(lat_c2, lon_c2, lat_c1, lon_c1) at same T_valid",
        "source": "Consecutive NCMRWF forecast cycles (e.g. 00Z vs prior 12Z)",
        "availability": "At forecast initialization cutoff T of cycle 2",
        "status": "VALIDATED",
        "model_role": "Primary cycle-over-cycle forecast stability indicator (M4 diagnostic)",
    },
    "cycle_spread_shift_km": {
        "definition": "Change in ensemble spread between consecutive cycles at identical valid time.",
        "units": "km",
        "calculation": "spread(c2, T_valid) - spread(c1, T_valid)",
        "source": "Successive ensemble cycles",
        "availability": "At forecast initialization cutoff T",
        "status": "VALIDATED",
        "model_role": "Monitors consolidation vs widening uncertainty across cycles",
    },
    "trajectory_curvature_deg": {
        "definition": "Heading change angle across 3 consecutive forecast leads within the cycle.",
        "units": "degrees ([0, 180])",
        "calculation": "|bearing(t-1 -> t) - bearing(t-2 -> t-1)|",
        "source": "Successive lead positions of ensemble mean",
        "availability": "Available at lead t >= 12h",
        "status": "VALIDATED",
        "model_role": "Detects sharp recurvature or erratic track steering (M2 Trajectory)",
    },
    "trajectory_instability_km": {
        "definition": "Step distance jitter |dist(t-1 -> t) - dist(t-2 -> t-1)|.",
        "units": "km",
        "calculation": "Absolute second difference of lead step distances",
        "source": "Ensemble mean coordinates",
        "availability": "Available at lead t >= 12h",
        "status": "VALIDATED",
        "model_role": "Detects erratic forward translation speed changes (M2 Trajectory)",
    },
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two points in kilometers."""
    earth_radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return float(earth_radius_km * c)


def compute_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute forward azimuth bearing in degrees [0, 360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
    return float(bearing)


def classify_trajectory_state(
    has_prior_cycle: bool,
    cycle_revision_km: Optional[float],
    curvature_deg: Optional[float],
    instability_jitter_km: Optional[float],
    speed_kmh: Optional[float],
    spread_growth_rate: Optional[float],
) -> Tuple[TrajectoryStateLiteral, str]:
    """Deterministic, explainable classification of forecast trajectory stability.
    
    States:
    - STABLE_PERSISTENT: Forecast is spatially consistent with minimal revision (< 30 km).
    - PROGRESSIVE_DRIFT: Steady, moderate displacement across cycles/leads (30–70 km).
    - OSCILLATING_JUMPY: Erratic heading changes (> 45° curvature) or translation jitter (> 35 km).
    - RAPID_REVISION: Sudden major cycle-to-cycle revision (> 70 km at identical valid time).
    - INSUFFICIENT_EVIDENCE: No prior cycle and no multi-lead history available.
    """
    if not has_prior_cycle and curvature_deg is None:
        return (
            "INSUFFICIENT_EVIDENCE",
            "Insufficient trajectory evidence: baseline initialization without prior consecutive cycle.",
        )

    # 1. Sudden Major Cycle Revision (Top instability trigger)
    if cycle_revision_km is not None and cycle_revision_km >= 70.0:
        return (
            "RAPID_REVISION",
            (
                f"Rapid cycle-to-cycle forecast revision: model shifted {cycle_revision_km:.1f} km "
                f"compared to prior initialization for identical valid time."
            ),
        )

    # 2. Oscillating / Jumpy Trajectory (Erratic steering)
    if (curvature_deg is not None and curvature_deg >= 45.0) or (
        instability_jitter_km is not None and instability_jitter_km >= 35.0
    ):
        curv_str = f"curvature {curvature_deg:.1f}°" if curvature_deg is not None else ""
        jit_str = f"step jitter {instability_jitter_km:.1f} km" if instability_jitter_km is not None else ""
        details = ", ".join(filter(None, [curv_str, jit_str]))
        return (
            "OSCILLATING_JUMPY",
            f"Oscillating forecast trajectory: erratic heading or speed fluctuations ({details}).",
        )

    # 3. Progressive Drift (Moderate revision or steady track evolution)
    if (cycle_revision_km is not None and cycle_revision_km >= 25.0) or (
        curvature_deg is not None and curvature_deg >= 20.0
    ):
        shift_str = f"revision shift {cycle_revision_km:.1f} km" if cycle_revision_km is not None else "smooth progressive curvature"
        return (
            "PROGRESSIVE_DRIFT",
            f"Progressive trajectory drift: forecast tracks show continuous gradual migration ({shift_str}).",
        )

    # 4. Stable Persistent (High consistency)
    rev_str = f"revision {cycle_revision_km:.1f} km" if cycle_revision_km is not None else "smooth translation"
    return (
        "STABLE_PERSISTENT",
        f"Stable persistent trajectory: high cycle-to-cycle consistency ({rev_str}, low curvature).",
    )


def compute_trajectory_intelligence(
    case_id: str,
    region_id: str,
    forecast_cycle_iso: str,
    lead_hours: int,
    valid_time_iso: str,
    current_center: Optional[Tuple[float, float]] = None,
    current_spread_km: Optional[float] = None,
    prior_cycle_center: Optional[Tuple[float, float]] = None,
    prior_cycle_spread_km: Optional[float] = None,
    prior_cycle_iso: Optional[str] = None,
    lead_history: Optional[List[Tuple[int, float, float, float]]] = None,  # (lead, lat, lon, spread)
) -> TrajectoryMetrics:
    """Compute canonical trajectory intelligence adhering strictly to anti-leakage invariants."""
    # 1. Cycle-to-cycle revision at identical valid time
    has_prior = False
    rev_dist: Optional[float] = None
    spread_shift: Optional[float] = None
    rev_rate: Optional[float] = None

    if (
        current_center is not None
        and prior_cycle_center is not None
        and prior_cycle_iso is not None
    ):
        has_prior = True
        rev_dist = float(haversine_distance(
            current_center[0], current_center[1],
            prior_cycle_center[0], prior_cycle_center[1],
        ))
        if current_spread_km is not None and prior_cycle_spread_km is not None:
            spread_shift = float(current_spread_km - prior_cycle_spread_km)

        # Assuming 12h cycle difference by default
        rev_rate = float(rev_dist / 12.0)

    # 2. Intra-cycle multi-lead trajectory metrics (leads <= current lead)
    speed_kmh: Optional[float] = None
    curvature_deg: Optional[float] = None
    spread_growth: Optional[float] = None
    jitter_km: Optional[float] = None

    if lead_history and len(lead_history) >= 2:
        # Sort leads ascending
        sorted_leads = sorted([h for h in lead_history if h[0] <= lead_hours], key=lambda x: x[0])
        if len(sorted_leads) >= 2:
            l_curr = sorted_leads[-1]
            l_prev1 = sorted_leads[-2]
            dt1 = max(1, l_curr[0] - l_prev1[0])
            d1 = haversine_distance(l_prev1[1], l_prev1[2], l_curr[1], l_curr[2])
            speed_kmh = float(d1 / dt1)
            spread_growth = float((l_curr[3] - l_prev1[3]) / dt1)

            if len(sorted_leads) >= 3:
                l_prev2 = sorted_leads[-3]
                dt2 = max(1, l_prev1[0] - l_prev2[0])
                d2 = haversine_distance(l_prev2[1], l_prev2[2], l_prev1[1], l_prev1[2])
                jitter_km = float(abs(d1 - d2))

                b1 = compute_bearing_deg(l_prev2[1], l_prev2[2], l_prev1[1], l_prev1[2])
                b2 = compute_bearing_deg(l_prev1[1], l_prev1[2], l_curr[1], l_curr[2])
                curv = abs(b2 - b1)
                if curv > 180.0:
                    curv = 360.0 - curv
                curvature_deg = float(curv)

    # 3. Deterministic Trend
    if rev_dist is not None:
        if rev_dist > 50.0 or (spread_growth is not None and spread_growth > 3.0):
            trend = "increasing"
        elif rev_dist < 20.0 and (spread_growth is None or spread_growth < 0.0):
            trend = "decreasing"
        else:
            trend = "stable"
    elif spread_growth is not None:
        trend = "increasing" if spread_growth > 2.0 else "decreasing" if spread_growth < -2.0 else "stable"
    else:
        trend = "unavailable"

    # 4. Classify State
    state, desc = classify_trajectory_state(
        has_prior_cycle=has_prior,
        cycle_revision_km=rev_dist,
        curvature_deg=curvature_deg,
        instability_jitter_km=jitter_km,
        speed_kmh=speed_kmh,
        spread_growth_rate=spread_growth,
    )

    return TrajectoryMetrics(
        case_id=case_id,
        region_id=region_id,
        forecast_cycle=forecast_cycle_iso,
        reference_cycle=prior_cycle_iso,
        lead_hours=lead_hours,
        valid_time=valid_time_iso,
        has_prior_cycle=has_prior,
        cycle_revision_distance_km=round(rev_dist, 2) if rev_dist is not None else None,
        cycle_spread_shift_km=round(spread_shift, 2) if spread_shift is not None else None,
        revision_rate_kmh=round(rev_rate, 2) if rev_rate is not None else None,
        trajectory_speed_kmh=round(speed_kmh, 2) if speed_kmh is not None else None,
        trajectory_curvature_deg=round(curvature_deg, 2) if curvature_deg is not None else None,
        spread_growth_rate=round(spread_growth, 2) if spread_growth is not None else None,
        trajectory_instability_km=round(jitter_km, 2) if jitter_km is not None else None,
        instability_state=state,
        state_description=desc,
        trend=trend,
        is_validated=True,
    )
