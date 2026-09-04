# M0 Data Reality Check — NCMRWF / TIGGE Sample Report

**Milestone**: M1.1 (Data Reality & Ingestion Foundation)  
**Date**: September 4, 2026  
**Status**: VERIFIED & REPRODUCED  
**Source File**: `data/raw/tigge/67603f4734166cde0f2c2962323ad8e4.grib`  
**File Size**: 1,235,344 bytes  
**SHA-256 Checksum**: `37cfccaac79bc952bb00641b3b9bf3b07e4d984ba867b950dd727624bca46d0b`  

---

## 1. Context & Purpose

This document records the first verified real meteorological data sample ingested into the ForecastGuard project, fulfilling the Milestone 0 / Milestone 1.1 requirements described in `ARCHITECTURE.md` (Sections 381–438) and `SCIENCE_SPEC.md`.

In strict accordance with the project constitution (`AGENTS.md`):
- **No data are fabricated.**
- **No machine learning models, bust predictions, or risk scores are claimed or executed.**
- **No simulated data are presented as real observations.**
- **Demonstrated values reflect only direct, verifiable metadata and calculations from the raw file.**

---

## 2. ECMWF / ECDS Data Retrieval Context

### What Was Requested
The authorized data request submitted to the ECMWF Data Store (ECDS) for TIGGE NCMRWF forecasts specified:
- **Origin / Centre**: NCMRWF (India) (`dems`)
- **Initialization Date**: 2025-09-01
- **Initialization Cycle**: 00:00 UTC
- **Level Type**: Single level / surface
- **Requested Variable**: Total precipitation (`tp`)
- **Forecast Type**: Perturbed ensemble forecast (`pf`), all available members
- **Forecast Lead Step**: +24 hours
- **Spatial Bounding Box**: 20°N to 10°N, 70°E to 90°E (subregion of peninsular India / Bay of Bengal / Arabian Sea)
- **Format**: GRIB2

### What Was Actually Returned
The returned GRIB2 file contained **44 GRIB messages**, including not only the requested variable (`tp`), but also three additional co-retrieved surface variables:
- `2t` (2-metre temperature)
- `msl` (Mean sea level pressure)
- `tcc` (Total cloud cover)
- `tp` (Total precipitation)

> **Key Architectural Rule**: Ingestion pipelines must never assume a returned file contains solely the requested variable. All messages in the payload must be inspected, catalogued, and routed explicitly.

---

## 3. Comparison: Manual Inspection vs Ingestion Software Output

The table below confirms the alignment between manual direct inspection (via interactive ecCodes shell calls) and the automated parsing produced by `scientific/ingestion/grib.py`:

| Parameter | Manually Verified Observation | Software Ingestion Output | Concordance |
| :--- | :--- | :--- | :--- |
| **Total Message Count** | 44 | 44 | **Exact Match** |
| **GRIB Edition** | 2 | 2 | **Exact Match** |
| **Unique Variables** | `2t`, `msl`, `tcc`, `tp` | `['2t', 'msl', 'tcc', 'tp']` | **Exact Match** |
| **Forecast Type** | `pf` (perturbed forecast) | `['pf']` | **Exact Match** |
| **Ensemble Members** | 1 through 11 (11 members) | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]` | **Exact Match** |
| **Forecast Init Date** | 2025-09-01 | `20250901` | **Exact Match** |
| **Forecast Init Time** | 00:00 UTC | `0000 UTC` | **Exact Match** |
| **Forecast Step** | 24 h | `24` | **Exact Match** |
| **Grid Type** | `regular_ll` | `regular_ll` | **Exact Match** |
| **Ni (Longitudes)** | 112 | 112 | **Exact Match** |
| **Nj (Latitudes)** | 83 | 83 | **Exact Match** |
| **First Grid Point** | (19.92°N, 70.02°E) | (19.92°N, 70.02°E) | **Exact Match** |
| **Last Grid Point** | (10.08°N, 90.00°E) | (10.08°N, 90.00°E) | **Exact Match** |
| **Grid Increments** | Δi = 0.18°, Δj = 0.12° | Δi = 0.18°, Δj = 0.12° | **Exact Match** |
| **Values Per Field** | 9,296 (112 × 83) | 9,296 | **Exact Match** |

---

## 4. Precipitation (`tp`) Semantics & Verification

The total precipitation messages in this sample exhibit the following authoritative metadata:
- **`shortName`**: `tp`
- **`name`**: Total Precipitation
- **`units`**: `kg m**-2` (equivalent to mm water equivalent)
- **`stepType`**: `accum` (accumulated variable)
- **`startStep`**: `0`
- **`endStep`**: `24`

### Accumulation Interpretation
The metadata confirms that each `tp` message in this file represents rainfall accumulated over the interval **from hour 0 to hour 24** after the 2025-09-01 00:00 UTC initialization cycle.

> **Accumulation Contract**: Because `startStep = 0` and `endStep = 24`, this field represents a 24-hour accumulation starting at initialization, not an incremental 6-hour or 12-hour sub-step. Any future verification against observations (e.g. IMD gridded rainfall) must compare against an observation window matching exactly the physical accumulation period (2025-09-01 00:00 UTC to 2025-09-02 00:00 UTC).

---

## 5. Numerical Integrity & Sanity Checks

Every individual field was numerically scanned across its 9,296 grid points.

### Total Precipitation Member 1 Benchmark:
- **Number of Points**: 9,296
- **Minimum**: `0.00177001953125` kg m⁻²
- **Maximum**: `164.741455078125` kg m⁻²
- **Mean**: `12.199371452791144` kg m⁻²
- **NaN Count**: `0`
- **Negative Value Count**: `0`

### Multi-Member Spread (Precipitation Summary Across All 11 Perturbed Members):
- Across all 11 perturbed ensemble members (1 to 11), precipitation maximums range from **93.85 kg m⁻²** (member 9) to **223.14 kg m⁻²** (member 10).
- Mean rainfall across the spatial domain varies between **11.20 kg m⁻²** and **13.97 kg m⁻²**.
- **Zero negative precipitation values** were detected across all members.
- **Zero NaN values** were detected across all members.

### Secondary Variables Summary (Sanity Check):
- **2-metre Temperature (`2t`)**: Minimum ~287.5 K, Maximum ~303.3 K (~14.4°C to 30.2°C). Zero NaNs, physically realistic for peninsular India in early September.
- **Mean Sea Level Pressure (`msl`)**: Minimum ~99,803 Pa, Maximum ~100,915 Pa (~998 to 1009 hPa). Physically plausible synoptic pressure distribution.
- **Total Cloud Cover (`tcc`)**: Values span 1.0% to 100.0% with domain averages ~88%–95%, consistent with active monsoon cloud cover.

---

## 6. Critical Caveats & Scientific Scope Limitations

1. **Subregion Sample Only**:  
   This sample covers a bounded spatial box (10.08°N–19.92°N, 70.02°E–90.00°E) and a single forecast step (+24 h). It does **NOT** constitute a complete national India domain (typically ~6.5°N–38.5°N, 66.5°E–100.0°E), nor does it cover medium-range forecast lead times (D+3 to D+10).
2. **Single Forecast Cycle**:  
   This sample represents only one initialization cycle (2025-09-01 00:00 UTC). Run-to-run consistency or forecast trajectory cannot be evaluated from a single cycle.
3. **Absence of Ground Truth Observations in this File**:  
   This file contains forecast data only. No observed rainfall data (e.g. IMD merged gauge/satellite analysis) are present. Forecast error cannot be computed until matching observations are ingested and aligned in later milestones.
4. **No ML or Bust Risk Score**:  
   This milestone demonstrates data ingestion, format parsing, and non-destructive QC. No machine learning models, bust indicators, or operational risk ratings are claimed.

---

## 7. Artifact Generated

- **Deterministic JSON Manifest**: `data/manifests/67603f4734166cde0f2c2962323ad8e4_manifest.json`  
  Generated automatically by `scientific.ingestion.grib.generate_manifest()`. Contains message inventory, dimensions, QC flags, and per-message statistics for reproducible downstream processing.
