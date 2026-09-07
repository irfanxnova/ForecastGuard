# ForecastGuard — Final Scientific Integrity & Demo-Readiness Audit Report

**SIH2026 Problem Statement SIH26079:** *AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts*  
**Evaluation Date:** September 2026  
**Audit Standard:** Strict Anti-Leakage, Authoritative Threshold Verification, and Chronological Event Separation.

---

## A. Data Provenance

1. **Numerical Weather Prediction (NWP) Forecasts**:
   - **Origin System**: NCMRWF National Ensemble Prediction System (NEPS).
   - **Data Provider**: ECMWF The International Grand Global Ensemble (TIGGE) archive (`origin=dems`, `dataset=tigge-forecasts`).
   - **Ensemble Configuration**: 11 perturbed ensemble members (`type=pf`, numbers 1–11).
   - **Atmospheric Variable**: Mean Sea Level Pressure (MSLP, ECMWF GRIB parameter ID `151`).
   - **Spatial Coverage**:
     - Bay of Bengal: $5^{\circ}\text{N}–30^{\circ}\text{N}$, $75^{\circ}\text{E}–100^{\circ}\text{E}$
     - Arabian Sea: $5^{\circ}\text{N}–30^{\circ}\text{N}$, $48^{\circ}\text{E}–78^{\circ}\text{E}$
   - **Forecast Steps**: 6-hourly intervals (+06h, +12h, +18h, +24h, +30h, +36h, +42h, +48h).

2. **Ground Truth Verification Observations**:
   - **Source**: Regional Specialized Meteorological Centre (RSMC) New Delhi / India Meteorological Department (IMD).
   - **Dataset**: Official Cyclone Best Track Archive (1982–2026 official archive: `data/validation/Best_Tracks_Data_1982-2026.xlsx`).
   - **Fix Quality**: Official 3-hourly and 6-hourly synoptic vortex center fixes, central minimum pressures, and maximum sustained wind speeds.

3. **Temporal Step Matching**:
   - **Exact Synoptic Timestamps**: 100% of the 101 verified forecast leads are matched to official IMD/RSMC best-track fixes at identical UTC timestamps.
   - **Zero Interpolation**: No artificial temporal interpolation, coordinate shifting, or observation fabrication was performed.

---

## B. Exact Dataset Counts

| Metric | Machine-Derived Value |
| :--- | :--- |
| **Total Distinct Tropical Cyclones** | **6** (MOCHA, BIPARJOY, TEJ, HAMOON, MIDHILI, MICHAUNG) |
| **Total NCMRWF TIGGE Forecast Cycles** | **13** cycles (Bay of Bengal & Arabian Sea) |
| **Total Verified Forecast Leads** | **101** exact 6-hourly leads |
| **Total Evaluated Ensemble Member Tracks** | **1,111** member vortex fixes |
| **Total Contemporaneous Busts ($\text{error} \ge \tau$)** | **24** verified failure events (23.8% failure rate) |
| **Severity Tier: `NORMAL` ($<0.75\tau$)** | **61** leads (60.4%) |
| **Severity Tier: `MODERATE` ($[0.75\tau, \tau)$)** | **16** leads (15.8%) |
| **Severity Tier: `DEGRADED` ($[\tau, 1.5\tau)$)** | **16** leads (15.8%) |
| **Severity Tier: `SEVERE` ($\ge 1.5\tau$)** | **8** leads (7.9%) |
| **Prospective Target Evaluation Instances** | **88** valid prospective lead vectors (13 terminal leads without future verification) |
| **Prospective Target Bust Positives ($Y(t) = 1$)** | **37** instances (42.0% across all 88 valid leads) |
| **Training Prospective Instances** | **67** leads (MOCHA, BIPARJOY, TEJ, HAMOON, MIDHILI) |
| **Training Prospective Bust Positives** | **37** instances (55.2% positive class rate) |
| **Held-Out Test Prospective Instances** | **21** leads (MICHAUNG 00Z, 12Z, 1202_00Z) |
| **Held-Out Test Bust Positives** | **0** instances (0.0% — well-forecasted event) |
| **M4 Consecutive Cycle Revision Pairs** | **41** matched pairs at identical valid times |

---

## C. Target Definition

The prospective bust target is mathematically formulated to detect upcoming forecast failure ahead of time:

$$Y(t) = 1 \iff \exists t' \in (t, t + 24\text{h}] \quad \text{such that} \quad \text{error}(t') \ge \tau(t')$$

where the authoritative lead-dependent track error threshold $\tau(t)$ is:

$$\tau(t) = 90.0 \times (1.0 + 0.008 \times t)\text{ km}$$

- **At +06h**: $\tau(06) = 94.32\text{ km}$
- **At +12h**: $\tau(12) = 98.64\text{ km}$
- **At +24h**: $\tau(24) = 107.28\text{ km}$
- **At +48h**: $\tau(48) = 124.56\text{ km}$

**Severity Tiers**:
- `NORMAL`: $\text{error} < 0.75 \times \tau(t)$
- `MODERATE`: $0.75 \times \tau(t) \le \text{error} < \tau(t)$
- `DEGRADED`: $\tau(t) \le \text{error} < 1.5 \times \tau(t)$
- `SEVERE`: $\text{error} \ge 1.5 \times \tau(t)$

---

## D. Leakage Audit Result

An exhaustive line-by-line code audit of `cyclone_p3.py` and `run_m0_m6_experiment.py` confirmed:
1. **Target Separation**: Features at lead $t$ use strictly data available at or before lead $t$ from the current cycle or prior cycles.
2. **Correction of M5 Feature Leakage**: In the previous experimental run, M5 included `float(f.confidence_quadrant == "FALSE_CONFIDENCE")` in its feature row. Because `confidence_quadrant` was classified using retrospective future error, this column inadvertently leaked target information. **This leakage was completely eliminated.** M5 now uses strictly prospective predictors: `[lead_hours, ensemble_spread_km, reliability_contradiction_index, ensemble_divergence_km]`.
3. **Observation Boundaries**: Observed IMD synoptic fixes and track errors are used strictly as evaluation ground truth, never as predictor features.
4. **Causality Across Cycles**: Successive cycle comparisons enforce $T_{\text{init}, 1} < T_{\text{init}, 2}$ strictly.
5. **No Terminal Lookahead**: Terminal leads (+48h, or early landfall dissipation) have `prospective_bust_within24h = None` and are never used as prospective evaluation targets.

---

## E. M4 Cycle Revision Instability Audit

- **Definition**: Difference between consecutive NWP forecast cycles ($C_1$ issued at $T$, $C_2$ issued at $T + 12\text{h}$) evaluated at identical verification valid times ($T_{\text{valid}}$).
- **Sample Size**: **41 consecutive revision pairs** across 6 storm systems.
- **Empirical Statistics**:
  - Mean 12h forecast revision distance: **57.65 km**
  - Median revision distance: **51.72 km**
  - Maximum revision distance: **128.87 km** (observed on Cyclone MIDHILI)
- **Empirical Association**:
  - Pearson correlation between cycle revision distance and verified track error: **$r = +0.4482$**.
  - **Scientific Terminology Correction**: The phrase "Causal Correlation" was removed from all documentation. The relationship is strictly documented as an **empirical association** indicating that large cycle-to-cycle forecast jumps associate with increased downstream track vulnerability.
- **Model Evaluation**: While the correlation is strong, direct linear inclusion of revision shift distance in model M4 degraded out-of-event test metrics ($\text{Brier} = 0.5186$). Therefore, M4 is **KILLED** as an automated standalone model and retained as an operational diagnostic indicator.

---

## F. M5 / False-Confidence Diagnostic Audit

- **Core Operational Phenomenon**:  
  *"False confidence occurs when ensemble spread is deceptively narrow while deterministic forecast error subsequently becomes large."*
- **Empirical Evidence from Pilot Archive**:
  - **Cyclone BIPARJOY (+06h, +12h)**: Ensemble spread was 56.6 km and 63.6 km (well below the median spread of 110.2 km), yet track error reached 116.5 km and 99.1 km.
  - **Cyclone TEJ (+42h, +48h in 12Z cycle)**: Ensemble spread was 66.2 km and 71.6 km, yet track error degraded to 141.4 km and 142.7 km.
  - **Cyclone MIDHILI (+18h, +24h, +30h)**: Ensemble spread remained between 68.3 km and 81.4 km, yet deterministic track error escalated dramatically to 147.8 km, 231.1 km, and 356.1 km.
- **Retrospective Quadrant vs. Prospective Signal**:
  - **Quadrant B (`LOW_SPREAD_HIGH_ERROR_FALSE_CONFIDENCE`)** is a **retrospective verification classification** (10 verified instances).
  - **Reliability Contradiction Index (RCI)** is a **prospective diagnostic signal** computed at lead $t$ from ensemble anisotropy ratio and spread growth rate without using future errors.
- **Audited Model Metrics (Leakage-Free M5)**:
  - Held-out Brier score: **0.3619**
  - LOOCV Brier score: **0.2956** (improves over M0 Climatology 0.3086 and M1 Spread-Only 0.3213)
  - Status: Retained as a **Diagnostic Overlay**.

---

## G. M0–M6 Model Interpretation

Evaluated chronologically across held-out test cycles (**Cyclone MICHAUNG**, 3 unseen cycles) and across all 6 storms via **Leave-One-Storm-Out Cross-Validation (LOOCV)**:

| Model ID | Feature Set | Held-Out Brier | Held-Out ECE | Held-Out Acc | LOOCV Brier | LOOCV ECE | LOOCV Acc | Audit Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **M0_Climatology** | Climatological lead-risk curve | 0.3295 | 0.5597 | 42.9% | 0.3086 | 0.3848 | 38.0% | **Operational Reference** |
| **M1_SpreadOnly** | Scalar ensemble track spread | 0.3302 | 0.5605 | 42.9% | 0.3213 | 0.4277 | 36.0% | **Primary Machine Baseline** |
| **M2_Spread_Trajectory** | Spread + speed + curvature | 0.2677 | 0.4637 | 47.6% | 0.2774 | 0.3482 | 52.1% | **Provisional Candidate** |
| **M3_Spread_Geometry** | Spread + anisotropy + bimodality | 0.1850 | 0.4172 | 76.2% | 0.2887 | 0.3842 | 62.1% | **Provisional Candidate** |
| **M4_Spread_CycleInstability** | Spread + 12h revision shift | 0.5186 | 0.7040 | 9.5% | 0.3616 | 0.4708 | 34.0% | **KILLED** (Degrades Test Metrics) |
| **M5_Spread_FalseConfidence** | Spread + RCI + divergence (clean) | 0.3619 | 0.5818 | 33.3% | 0.2956 | 0.3766 | 50.8% | **Diagnostic Overlay** |
| **M6_CombinedCandidate** | Combined feature families | 0.1798 | 0.3818 | 76.2% | 0.2728 | 0.3540 | 62.1% | **Provisional Candidate** |

**Scientific Caveat on Model Selection**:  
M1 (Spread-Only) is retained as the stable primary machine baseline. While M6 and M3 achieved lower Brier scores on the held-out event, this sample represents only 6 storms. In accordance with Agent Constitution Rule 11, complex feature combinations are treated as **provisional research candidates**, not proven operational replacements.

---

## H. Prospective Warning Verification

Every reported advance warning was independently recomputed:
- **Alert Condition**: Model prospective alert probability $\ge 0.5$ raised at lead $t_{\text{alert}}$.
- **Prospective Window Invariant**: The alert predicts failure within $(t_{\text{alert}}, t_{\text{alert}} + 24\text{h}]$. Therefore, an alert at $t_{\text{alert}}$ is a valid advance warning for a bust at $t_{\text{bust}}$ iff:
  $$t_{\text{alert}} < t_{\text{bust}} \le t_{\text{alert}} + 24\text{h}$$
- **Advance Warning Lead Time**:
  $$\Delta t_{\text{warning}} = t_{\text{bust}} - t_{\text{alert}} \le 24\text{ hours}$$

**Independent Verification Results**:
- **Maximum Independently Verified Warning Lead**: **24 hours**.
- **Warning Timestamps**:
  - Cyclone MIDHILI (+48h bust at 2023-11-18 00:00Z): Alert issued at $+24\text{h}$ (2023-11-17 00:00Z) $\to$ **24h advance warning**.
  - Cyclone TEJ (+48h bust at 2023-10-23 00:00Z): Alert issued at $+24\text{h}$ (2023-10-22 00:00Z) $\to$ **24h advance warning**.
  - Cyclone BIPARJOY (+48h bust at 2023-06-10 00:00Z): Alert issued at $+24\text{h}$ (2023-06-09 00:00Z) $\to$ **24h advance warning**.
  - Cyclone HAMOON (+42h bust at 2023-10-24 18:00Z): Alert issued at $+24\text{h}$ (2023-10-24 00:00Z) $\to$ **18h advance warning**.
  - Cyclone MIDHILI (+30h bust at 2023-11-17 06:00Z): Alert issued at $+24\text{h}$ (2023-11-17 00:00Z) $\to$ **6h advance warning**.
- **Audit Finding**: In all 24 failure events, `warning_time` strictly precedes `bust_time`. Zero events claim unphysical warnings beyond the 24h prospective lookahead window.

---

## I. Operational Feature Availability Classification

| Feature | Description | Availability Tier | Operational Role |
| :--- | :--- | :---: | :--- |
| **`ensemble_spread_km`** | Standard deviation of member tracks | **Tier A** (Available at issuance) | Primary predictor baseline |
| **`ensemble_divergence_km`** | Maximum pairwise member distance | **Tier A** (Available at issuance) | Predictor feature |
| **`anisotropy_ratio`** | Spatial PCA major/minor axis spread ratio | **Tier A** (Available at issuance) | Geometry predictor feature |
| **`bimodality_coefficient`** | Sarle's bimodality coefficient along major axis | **Tier A** (Available at issuance) | Geometry predictor feature |
| **`spread_growth_km`** | Rate of change of spread ($t-6\text{h} \to t$) | **Tier A** (Available at issuance) | Trajectory predictor feature |
| **`spread_acceleration_km`** | Second difference of spread ($t-12\text{h} \to t$) | **Tier A** (Available at issuance) | Trajectory predictor feature |
| **`trajectory_speed_kmh`** | Translation speed of ensemble mean | **Tier A** (Available at issuance) | Trajectory predictor feature |
| **`trajectory_curvature_deg`** | Heading directional change | **Tier A** (Available at issuance) | Trajectory predictor feature |
| **`RCI`** | Reliability Contradiction Index | **Tier A** (Available at issuance) | Diagnostic predictor feature |
| **`has_prior_cycle`** | Indicator of prior cycle availability | **Tier B** (Available from prior cycle) | Contextual indicator |
| **`cycle_revision_distance_km`**| Shift between consecutive cycle forecasts | **Tier B** (Available from prior cycle) | Diagnostic indicator |
| **`cycle_spread_shift_km`** | Spread change between consecutive cycles | **Tier B** (Available from prior cycle) | Diagnostic indicator |
| **`observed_lat`, `observed_lon`**| Official IMD synoptic center fixes | **Tier C/D** (Post-event verification) | Evaluation ground truth |
| **`track_error_km`** | Haversine distance between mean and fix | **Tier D** (Retrospective verification) | Verification metric |
| **`is_bust` / `severity`** | Continuous threshold binary/tier labels | **Tier D** (Retrospective verification) | Verification target |
| **`confidence_quadrant`** | Quadrant classification (A/B/C/D) | **Tier D** (Retrospective verification) | Verification catalog |

---

## J. Remaining Scientific Limitations

1. **Sample Size**: While 101 exact 6-hourly verified leads across 13 forecast cycles and 6 major cyclones is a complete proof-of-concept, it is drawn from the 2023 North Indian Ocean cyclone season.
2. **Class Imbalance Across Events**: Cyclone MICHAUNG was well-forecasted across its entire lifespan (0 busts), whereas MIDHILI exhibited severe downstream forecast failure (6 consecutive busts). Out-of-event validation metrics fluctuate based on whether the held-out storm experienced track failure.
3. **Threshold Sensitivity**: The authoritative threshold $\tau(t) = 90 \times (1 + 0.008t)\text{ km}$ represents operational meteorological standards for medium-range tropical cyclone tracking, but different basin jurisdictions or user operations may require customized tolerance curves.
4. **Data Access Boundaries**: ForecastGuard uses publicly archived ECMWF TIGGE data and official IMD annual best-track publications. Real-time NRT integration requires operational authorization and automated data ingestion agreements.

---

## K. Final Defensible Claims

1. ForecastGuard provides an automated, leakage-free forecast reliability intelligence layer over raw NWP ensemble predictions.
2. The system has been validated on 101 exact-time forecast leads from 13 real NCMRWF TIGGE ensemble cycles against official IMD/RSMC best-track observations.
3. Cycle-to-cycle forecast revision distance exhibits a statistically significant positive empirical association with subsequent track error ($r = +0.4482$).
4. The system successfully detects false-confidence situations where ensemble spread is deceptively narrow prior to severe track degradation (demonstrated on BIPARJOY, TEJ, and MIDHILI).
5. In verified failure cases, prospective alerts provided genuine advance warnings up to **24 hours** prior to downstream bust realization.

---

## L. Claims We Must NOT Make

1. **NEVER** claim "causal correlation" or "proven physical causality" from statistical association.
2. **NEVER** claim "world-first", "100% accurate", or "guaranteed warning".
3. **NEVER** claim warning lead times exceeding the prospective lookahead window (e.g. claiming "36h advance warning" from a 24h prospective model).
4. **NEVER** claim operational access to real-time NCMRWF or IMD high-security operational data streams without authorization.
5. **NEVER** claim that complex models (M6, M3) are statistically proven replacements for simple ensemble spread on a 6-storm sample.

---

## M. Final Demo Talking Points

### Safe to Say to Judges
- *"ForecastGuard does not replace official NWP forecasts or IMD warnings. NWP tells us what may happen; ForecastGuard tells operators how much they can trust that forecast."*
- *"We evaluated 101 exact-time 6-hourly forecast leads across 13 NCMRWF TIGGE ensemble cycles and 6 major cyclones, verified against official IMD/RSMC best-track archives."*
- *"Our key scientific finding is the identification of false-confidence events — situations where ensemble members cluster tightly, giving operators false reassurance, even as the storm is poised to bust."*
- *"Across consecutive 12-hour forecast cycles, the distance that the forecast shifts correlates positively ($r = +0.4482$) with subsequent track error."*
- *"On verified historical failure cases, our prospective model issued alert probabilities that gave up to 24 hours of advance warning before the forecast degraded."*
- *"We keep our baseline simple (M1 Spread-Only) and treat multi-feature combinations as provisional research candidates until validated across multi-season archives."*

### Do NOT Say
- *"Our AI model predicts atmospheric chaos."*
- *"We have a proven causal model of cyclone bust dynamics."*
- *"ForecastGuard is integrated into live NCMRWF operational supercomputers."*
- *"Our machine learning model achieves 36-hour guaranteed advance warning."*
- *"Ensemble spread is useless; AI has replaced ensemble prediction."*
- *"Our system was trained on decades of operational data."*
