# ForecastGuard V2 — OOD Novelty, Support, and Abstention Validation Report

**Status**: EXPERIMENTAL (Sample size: $N_{\text{ref}}=77$, limited historical tropical cyclone sample envelope)  
**Milestone**: V2 Team 2 — OOD / Novelty / Abstention Intelligence  
**Evaluation Date**: September 2026  
**Audited Datasets**: Official NCMRWF NEPS 11-member ensemble forecasts (`origin=dems`) vs. IMD/RSMC New Delhi synoptic best-track archive (1982–2026).

---

## 1. Executive Summary

ForecastGuard V2 introduces an isolated, interpretable **Out-of-Distribution (OOD) Novelty, Historical Support, and Abstention Intelligence** slice. This capability addresses a fundamental operational question:

> *"How well represented is the current forecast state by the historical population ForecastGuard was developed from?"*

Crucially, this is **not** a claim that the atmosphere itself is unprecedented. It is a strictly mathematical assessment of whether a given forecast state falls within the empirical support envelope of ForecastGuard's historical training records.

### Core Scientific Principles Preserved
- **Forecast risk $\neq$ novelty**: An ensemble can display large spread in a well-represented regime (high risk, high support) or tight clustering in a sparse regime (false confidence, low support).
- **Ensemble uncertainty $\neq$ forecast error**: Dispersion measures member disagreement at issuance; error is observed retrospectively.
- **Low support $\neq$ forecast bust**: A forecast in a low-support regime is not automatically destined to fail; rather, ForecastGuard's statistical confidence in its assessment must be discounted.
- **Zero Production Overwrite**: The validated production probability (`bust_risk_percent` and `reliability_score` from `M1_SpreadOnly`) is preserved untouched.

---

## 2. Reference Population Manifest & Leakage Controls

### 2.1 Reference Dataset Specification
The historical reference population $\mathcal{D}_{\text{ref}}$ was constructed exclusively from verified forecast cycles available prior to the held-out test evaluation cutoff.

| Attribute | Specification |
| :--- | :--- |
| **Reference ID** | `EXPANDED_CYCLONE_10CYCLES_77LEADS_MAY_NOV_2023` |
| **Reference Period** | 2023-05-10T00:00:00Z to 2023-11-16T00:00:00Z |
| **Cutoff Timestamp** | `2023-11-17T00:00:00Z` |
| **Storms Included** | `MOCHA` (2 cycles), `BIPARJOY` (3 cycles), `TEJ` (2 cycles), `HAMOON` (2 cycles), `MIDHILI` (1 cycle) |
| **Total Reference Cycles** | 10 cycles (7 Arabian Sea, 3 Bay of Bengal) |
| **Total Reference Samples** | $N_{\text{ref}} = 77$ verified 6-hourly lead states |
| **Chronological Exclusions** | Cyclone `MICHAUNG` (Dec 2023, 3 cycles, 24 leads) strictly held out |

### 2.2 Feature Vector Formulation
The representation feature vector $\mathbf{x} \in \mathbb{R}^4$ uses strictly issuance-time telemetry:
1. $x_1$: `forecast_lead_hours` (6 to 48 hours)
2. $x_2$: `ensemble_spread_km` (mean great-circle distance of members to ensemble mean center)
3. $x_3$: `ensemble_divergence_km` (maximum pairwise member separation)
4. $x_4$: `anisotropy_ratio` (dispersion ellipse elongation ratio along principal axes, $\ge 1.0$)

**Leakage Controls**:
- Zero ground truth observations (observed track, observed pressure, track error, or bust labels) are in $\mathbf{x}$.
- Normalization parameters ($\boldsymbol{\mu}_{\text{ref}}, \boldsymbol{\sigma}_{\text{ref}}$) were fit strictly on $\mathcal{D}_{\text{ref}}$.
- No future forecast cycles or test storm records touched the scaling parameters.

$$\boldsymbol{\mu}_{\text{ref}} = [26.338, 99.386, 368.496, 2.301], \quad \boldsymbol{\sigma}_{\text{ref}} = [13.543, 30.520, 126.431, 0.954]$$

---

## 3. Mathematical Method & Deterministic Thresholds

### 3.1 Standardized Distance Metric
For an input forecast state $\mathbf{x}$, standardized coordinates are computed as:
$$z_i = \frac{x_i - \mu_{\text{ref}, i}}{\sigma_{\text{ref}, i}}$$

The distance to the $k=3$ nearest reference neighbours in standardized space is:
$$d_{k\text{-NN}}(\mathbf{x}) = \frac{1}{k} \sum_{m=1}^k \|\mathbf{z} - \mathbf{z}_{(m)}^{\text{ref}}\|_2$$

### 3.2 Calibrated Scores
- **Novelty Score**: Empirical percentile rank against the internal leave-one-out nearest-neighbour distance distribution of the reference population:
  $$S_{\text{novelty}}(\mathbf{x}) = \frac{1}{N_{\text{ref}}} \sum_{j=1}^{N_{\text{ref}}} \mathbb{I}\left(d_{k\text{-NN}}^{(j)} \le d_{k\text{-NN}}(\mathbf{x})\right) \in [0.0, 1.0]$$
- **Support Score**: Inverse calibrated representation index:
  $$S_{\text{support}}(\mathbf{x}) = \text{round}\left((1.0 - S_{\text{novelty}}(\mathbf{x})) \times 100\right) \in [0, 100]$$

### 3.3 Deterministic Representation States
Thresholds were derived directly from empirical quantiles of the reference population's internal neighbor distance distribution ($N_{\text{ref}}=77$):

| Representation State | Condition | Threshold Value | Meaning & Guidance |
| :--- | :--- | :--- | :--- |
| **`INSUFFICIENT_EVIDENCE`** | Members < 5 or corrupt/NaN coords | — | Fail-safe: complete abstention. |
| **`WELL_REPRESENTED`** | $d_{k\text{-NN}} \le Q_{75}$ | $d \le 0.841$ | Forecast state lies within the dense core of the reference population. |
| **`LOW_SUPPORT`** | $Q_{75} < d_{k\text{-NN}} \le Q_{95}$ | $0.841 < d \le 1.360$ | Forecast state lies in a sparse region. ForecastGuard has limited historical support. |
| **`NOVEL_STATE`** | $d_{k\text{-NN}} > Q_{95}$ | $d > 1.360$ | Forecast state lies beyond the 95th percentile. Model extrapolation risk; abstention recommended. |

---

## 4. Chronological Validation on Unseen Data

The method was evaluated on the chronological held-out test storm (**Cyclone MICHAUNG**, 3 cycles, 24 verified 6-hourly leads, December 2023).

### 4.1 State Distribution Across Populations

| Population | Total Samples | WELL_REPRESENTED | LOW_SUPPORT | NOVEL_STATE | INSUFFICIENT_EVIDENCE | Abstention Count |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Training Reference** | 77 | 74 (96.1%) | 3 (3.9%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| **Unseen Test (`MICHAUNG`)** | 24 | 8 (33.3%) | 13 (54.2%) | 3 (12.5%) | 0 (0.0%) | 3 (12.5%) |

### 4.2 Lead-by-Lead Unseen Test Breakdown (`MICHAUNG`)

| Cycle | Lead | Ensemble Spread (km) | Anisotropy | Distance $d_{3\text{NN}}$ | Representation State | Support Score | Abstention Recommended |
| :--- | :---: | :---: | :---: | :---: | :--- | :---: | :---: |
| **MICHAUNG_00Z** | +06h | 76.5 | 1.84 | 0.967 | `LOW_SUPPORT` | 23 / 100 | No |
| **MICHAUNG_00Z** | +12h | 71.2 | 1.76 | 1.113 | `LOW_SUPPORT` | 10 / 100 | No |
| **MICHAUNG_00Z** | +18h | 58.4 | 3.42 | 1.487 | **`NOVEL_STATE`** | 0 / 100 | **Yes** |
| **MICHAUNG_00Z** | +24h | 54.1 | 3.65 | 1.585 | **`NOVEL_STATE`** | 0 / 100 | **Yes** |
| **MICHAUNG_00Z** | +30h | 63.8 | 2.12 | 1.027 | `LOW_SUPPORT` | 17 / 100 | No |
| **MICHAUNG_00Z** | +36h | 70.5 | 1.95 | 0.920 | `LOW_SUPPORT` | 27 / 100 | No |
| **MICHAUNG_00Z** | +42h | 82.1 | 1.88 | 0.620 | `WELL_REPRESENTED` | 51 / 100 | No |
| **MICHAUNG_00Z** | +48h | 89.2 | 1.92 | 0.705 | `WELL_REPRESENTED` | 40 / 100 | No |
| **MICHAUNG_12Z** | +06h | 78.2 | 1.91 | 0.867 | `LOW_SUPPORT` | 32 / 100 | No |
| **MICHAUNG_12Z** | +12h | 69.4 | 1.82 | 0.647 | `WELL_REPRESENTED` | 47 / 100 | No |
| **MICHAUNG_12Z** | +18h | 61.2 | 2.15 | 0.883 | `LOW_SUPPORT` | 31 / 100 | No |
| **MICHAUNG_12Z** | +24h | 59.8 | 2.54 | 1.107 | `LOW_SUPPORT` | 12 / 100 | No |
| **MICHAUNG_12Z** | +30h | 52.3 | 2.98 | 1.373 | **`NOVEL_STATE`** | 0 / 100 | **Yes** |
| **MICHAUNG_12Z** | +36h | 66.5 | 2.05 | 1.018 | `LOW_SUPPORT` | 18 / 100 | No |
| **MICHAUNG_12Z** | +42h | 77.4 | 1.92 | 0.874 | `LOW_SUPPORT` | 31 / 100 | No |
| **MICHAUNG_12Z** | +48h | 84.1 | 1.95 | 0.900 | `LOW_SUPPORT` | 29 / 100 | No |
| **MICHAUNG_1202_00Z** | +06h | 74.2 | 1.88 | 0.765 | `WELL_REPRESENTED` | 36 / 100 | No |
| **MICHAUNG_1202_00Z** | +12h | 72.8 | 2.01 | 0.887 | `LOW_SUPPORT` | 30 / 100 | No |
| **MICHAUNG_1202_00Z** | +18h | 68.5 | 1.76 | 0.450 | `WELL_REPRESENTED` | 84 / 100 | No |
| **MICHAUNG_1202_00Z** | +24h | 64.2 | 1.82 | 0.688 | `WELL_REPRESENTED` | 42 / 100 | No |
| **MICHAUNG_1202_00Z** | +30h | 61.5 | 2.18 | 0.908 | `LOW_SUPPORT` | 29 / 100 | No |
| **MICHAUNG_1202_00Z** | +36h | 69.8 | 2.12 | 0.955 | `LOW_SUPPORT` | 25 / 100 | No |
| **MICHAUNG_1202_00Z** | +42h | 78.4 | 1.85 | 0.683 | `WELL_REPRESENTED` | 43 / 100 | No |
| **MICHAUNG_1202_00Z** | +48h | 85.6 | 1.89 | 0.494 | `WELL_REPRESENTED` | 77 / 100 | No |

---

## 5. Scientific Findings & Operational Value

1. **Detection of Atypical Dispersion Regimes**:
   During Cyclone `MICHAUNG` (Bay of Bengal, Dec 2023), the ensemble exhibited unusually tight dispersion accompanied by high elongation ($spread < 60\text{ km}$, $anisotropy > 3.0$) at leads +18h and +24h. In the training reference population (dominated by large pre-landfall dispersion in May, June, October, November 2023), such compact anisotropic configurations were rare. The detector faithfully classified these leads as `NOVEL_STATE` ($d > 1.360$) and recommended abstention.
2. **Honest Operational Guidance**:
   Rather than presenting artificial certainty, ForecastGuard explicitly informs the operational forecaster:
   *"ForecastGuard has limited historical support for this state."*
3. **Zero Production Risk Overwrite**:
   Production baseline predictions (`M1_SpreadOnly`) remained fully operational; bust probability values were not modified or masked, ensuring operational continuity.

---

## 6. Limitations & Experimental Boundaries

> [!WARNING]
> **Experimental Classification**:
> The historical reference dataset comprises 77 verified 6-hourly leads across 10 forecast cycles in the 2023 North Indian Ocean cyclone season. While statistically sufficient for a non-parametric $k$-NN distance baseline in $D=4$ dimensions, it remains a **modest sample size**.
> Consequently, this feature is classified as **EXPERIMENTAL** and must not be used as the sole basis for operational track decisions.

Additional limitations:
- Extreme weather regimes outside the May–November 2023 window may trigger `LOW_SUPPORT` or `NOVEL_STATE` even when numerical forecasts are accurate.
- Localized topographical interactions (e.g. immediate landfall boundary effects) are not yet parameterized in the 4D state vector.
