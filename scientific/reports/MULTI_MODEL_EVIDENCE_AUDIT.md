# ForecastGuard V2 — Multi-Model Forecast Agreement & NWP Evidence Audit

**Team**: Team 2 — Multi-Model Evidence & Decision-Support Layer  
**Date**: September 2026  
**Status**: `INSUFFICIENT_EVIDENCE` (Decision Gate Result) / `EXPERIMENTAL` (Agreement Metric Engine)  
**Governance Standard**: Strict Anti-Fabrication Constitution (`AGENTS.md`)  

---

## 1. Executive Summary & Core Question

This audit addresses the central question:
> **"Do genuinely independent forecast systems agree about the forecast state?"**

Multi-model agreement represents an **evidence layer** characterizing synoptic consensus dispersion across distinct numerical modeling systems. It is **not** automatically another bust probability model, and cross-system disagreement must **never** be equated with "forecast error".

In strict compliance with the project guidelines:
- **Zero data fabrication**: We do NOT simulate ECMWF, simulate UKMO, copy NCMRWF data under different names, generate fake multi-model curves, or invent disagreement values.
- **Decision Gate Outcome**: Because adequate real archives exist for **only one** NWP model locally (NCMRWF NEPS), the system returns **`INSUFFICIENT_EVIDENCE`**. This is a **successful, scientifically honest outcome** that protects meteorological decision-makers from synthetic illusions of consensus.

---

## 2. NWP Data Audit & Local Archive Inventory

An exhaustive inspection was conducted across all raw archives (`data/raw/`), manifests (`data/manifests/`), and verified regional datasets (`data/validation/`).

### Table 1: Model Archive Availability Matrix

| Model Identifier | Operational Centre | Country / Org | TIGGE Origin | Local Status | Verified Cyclone Leads | Historical Overlap | Variables Ingested |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NCMRWF_NEPS** | National Centre for Medium Range Weather Forecasting | India (MoES) | `dems` | **OPERATIONAL_ARCHIVED** | **101 leads** (13 cycles, 6 storms) | 100% (Baseline) | MSLP (`msl`), TP (`tp`), 2T (`2t`), TCC (`tcc`) |
| **ECMWF_IFS** | European Centre for Medium-Range Weather Forecasts | International | `ecmf` | **MISSING_ARCHIVE** | 0 leads | **0 leads** | None archived |
| **UKMO_GLOBAL** | Met Office | United Kingdom | `egrr` | **MISSING_ARCHIVE** | 0 leads | **0 leads** | None archived |
| **NCEP_GEFS** | National Centers for Environmental Prediction | USA (NOAA) | `kwbc` | **MISSING_ARCHIVE** | 0 leads | **0 leads** | None archived |

### Detailed Inventory of Usable System: NCMRWF NEPS
- **Centre**: NCMRWF, Ministry of Earth Sciences, New Delhi, India.
- **Source**: ECDS TIGGE Archive (`origin=dems`, `dataset=tigge-forecasts`).
- **Resolution**: $\Delta i = 0.18^\circ, \Delta j = 0.12^\circ$ (regional GRIB2) and $0.5^\circ$ (global TIGGE).
- **Cadence**: 6-hourly synoptic steps (+06h, +12h, +18h, +24h, +30h, +36h, +42h, +48h), 00Z and 12Z cycles.
- **Variables**: Mean Sea Level Pressure (vortex tracker), Total Precipitation (24h accumulation), 2-metre Temperature, Total Cloud Cover.
- **Historical Coverage**: May 2023 to December 2023.
  - MOCHA: 2 cycles (16 leads)
  - BIPARJOY: 3 cycles (24 leads)
  - TEJ: 2 cycles (18 leads)
  - HAMOON: 2 cycles (13 leads)
  - MIDHILI: 1 cycle (6 leads)
  - MICHAUNG: 3 cycles (24 leads)
- **Missingness**: 0 missing fields in verified cyclone database.

### Detailed Audit of Candidate Secondary Systems (ECMWF, UKMO, NCEP)
- **ECMWF IFS**: Ingestion pipeline code exists (`scientific/ingestion/tigge.py`), but no raw GRIB archives or vortex tracking records are stored locally in `data/`. The ECMWF host platform was utilized purely as a data transport portal (ECDS) to fetch Indian NCMRWF records.
- **UKMO & NCEP**: No local storage, no configuration files, and zero historical cycle overlap exist in the repository.

---

## 3. Decision Gate Evaluation

The Phase 2 Decision Gate specifies:
> *"If fewer than two genuinely independent and adequately aligned models are available: DO NOT build a fake scoring system. Implement only: multi-model availability contract, provenance contract, explicit INSUFFICIENT_EVIDENCE state, data-audit result, API representation."*

### Scientific Evaluation:
1. **Model Count**: 1 operational model < 2 required.
2. **Historical Cross-Model Pairs**: Exactly 0 paired leads across identical cyclones.
3. **Decision**: Return **`INSUFFICIENT_EVIDENCE`** for operational inference.
4. **Anti-Fabrication Enforcement**: No random perturbations, shifted coordinates, or synthetic ensemble members were generated.

---

## 4. Multi-Model Agreement Engine Architecture

To ensure operational readiness when secondary data is acquired, a pure, deterministic mathematical agreement engine was built in `scientific/ml/multimodel.py`:

### Prospective Feature Space
1. **Pairwise Great-Circle Track Separation** ($d_{ij}$):
   $$d_{ij} = \text{haversine}((\text{lat}_i, \text{lon}_i), (\text{lat}_j, \text{lon}_j))$$
2. **Mean and Maximum Cross-Model Separation**:
   $$d_{\text{mean}} = \frac{2}{n(n-1)} \sum_{i < j} d_{ij}, \quad d_{\text{max}} = \max_{i < j} d_{ij}$$
3. **MSLP Intensity Disagreement** ($\Delta P$):
   $$\Delta P = \max(P_k) - \min(P_k)$$

### Alignment Requirements:
- **Temporal Alignment**: All participating model fixes must share the identical UTC `valid_time` ($\Delta t = 0$).
- **Spatial Validation**: Coordinates must lie within physical bounds ($-90^\circ \le \text{lat} \le 90^\circ$, $-180^\circ \le \text{lon} \le 360^\circ$).
- **Model Independence**: Duplicate model IDs or centers are rejected.

### State Categorization & Experimental Thresholds:

| Agreement State | Track Separation ($d_{\text{max}}$) | Intensity Disagreement ($\Delta P$) | Scientific Interpretation |
| :--- | :--- | :--- | :--- |
| **`AGREEMENT`** | $\le 65.0\text{ km}$ | $\le 8.0\text{ hPa}$ | High cross-system consensus; independent models place vortex closely. |
| **`MODERATE_DISAGREEMENT`** | $65.0\text{ km} < d_{\text{max}} \le 150.0\text{ km}$ | $8.0\text{ hPa} < \Delta P \le 18.0\text{ hPa}$ | Noticeable cross-system dispersion; structural consensus divergence. |
| **`HIGH_DISAGREEMENT`** | $> 150.0\text{ km}$ | $> 18.0\text{ hPa}$ | Substantial cross-system divergence; elevated systemic synoptic uncertainty. |
| **`INSUFFICIENT_EVIDENCE`** | $<2$ valid models | N/A | Missing secondary model archive; consensus evaluation blocked. |

*Note: Thresholds are explicitly labeled **EXPERIMENTAL** because historical multi-model empirical calibration data is absent.*

---

## 5. Scientific Validation & Calibration Statement

Because zero independent model pairs exist locally, computing statistical validation metrics (such as Brier score, ECE, AUC, or warning lead time) on multi-model consensus would require fabricating synthetic forecasts.

In strict adherence to meteorological integrity:
- **Brier Score**: `N/A — Insufficient Data`
- **Expected Calibration Error (ECE)**: `N/A — Insufficient Data`
- **ROC AUC**: `N/A — Insufficient Data`
- **Promotion Status**: Classified as **`EXPERIMENTAL / INSUFFICIENT_EVIDENCE`**.
- **No Promotion to Probability Engine**: Multi-model consensus is preserved strictly as an **evidence overlay**, not a replacement or multiplier for the validated single-model baseline (`M1_SpreadOnly`).

---

## 6. Data Acquisition Roadmap to Operational Status

To transition multi-model agreement from `INSUFFICIENT_EVIDENCE` to a validated operational evidence layer, the following data acquisition specification is required:
1. **ECMWF IFS-ENS Retrieval**:
   - Query ECMWF ECDS TIGGE for `origin=ecmf` across the 13 historical cycles of MOCHA, BIPARJOY, TEJ, HAMOON, MIDHILI, and MICHAUNG.
   - Extract 6-hourly MSLP vortex fixes for ensemble mean and control run.
2. **NCEP GEFS Retrieval**:
   - Query TIGGE or NOAA NOMADS for `origin=kwbc` for the identical 13 cycles.
3. **Temporal Co-Registration**:
   - Align exactly at $T_{\text{valid}} \in \{00, 06, 12, 18\}\text{ UTC}$.
4. **Empirical Calibration**:
   - Calibrate separation thresholds against IMD RSMC Best Track verification to derive statistically grounded percentiles.

---

## 7. Non-Overclaim & Scientific Scope

### What This Module CLAIMS:
- Provides a transparent, auditable audit of regional NWP archive availability.
- Accurately reports `INSUFFICIENT_EVIDENCE` when secondary systems are missing.
- Computes great-circle separation and intensity disagreement deterministically when independent model fixes are supplied.

### What This Module DOES NOT CLAIM:
- **Does NOT claim model disagreement equals "forecast error" or "failure"**: Disagreement reflects cross-system consensus dispersion. A single outlier model may be correct while consensus fails.
- **Does NOT claim model agreement equals "forecast correctness"**: Multiple models can agree on a shared systemic bias (e.g. delayed recurvature in the Bay of Bengal).
- **Does NOT assert causal relationships**: Disagreement indicates synoptic divergence, not the physical cause of a downstream bust.
