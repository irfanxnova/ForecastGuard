# ForecastGuard — Scientific Report: M0→M6 Expansion & M4 Milestone
### Problem Statement SIH26079: AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts

---

## 14 Mandatory Scientific Answers

1. **How many storms?**
   **6 independent North Indian Ocean tropical cyclones** (BIPARJOY, HAMOON, MICHAUNG, MIDHILI, MOCHA, TEJ).

2. **How many forecast cycles?**
   **13 forecast cycles** retrieved directly from ECMWF/ECDS NCMRWF TIGGE NEPS (`origin=dems`, 11 perturbed ensemble members).

3. **How many exact-time verification pairs?**
   **101 exact 6-hourly verification pairs** matched against official IMD/RSMC New Delhi synoptic best-track fixes with zero interpolation.

4. **How many contemporaneous busts?**
   **24 verified contemporaneous failure events** exceeding the authoritative threshold:
   $$\tau(\text{lead}) = 90.0 \times (1.0 + 0.008 \times \text{lead})\text{ km}$$
   Breakdown:
   - `DEGRADED` ($\tau \le \text{error} < 1.5\tau$): 16 events
   - `SEVERE` ($\text{error} \ge 1.5\tau$): 8 events (including MIDHILI errors up to 548.5 km and HAMOON errors up to 298.7 km)

5. **How many prospective bust targets?**
   **88 prospective evaluation instances** ($t < t' \le t+24\text{h}$). (13 terminal horizon leads have no downstream verification within the 24h window).

6. **How many positive prospective cases?**
   **37 positive prospective bust cases** across the training cycles (55.2% class rate in training; 0% in held-out test event MICHAUNG).

7. **Does M1 improve over M0?**
   M1 (Scalar Ensemble Spread) achieves comparable calibration to M0 Climatology (Held-Out Brier: 0.3302 vs 0.3295; LOOCV Brier: 0.3213 vs 0.3086). M1 is retained as the primary physical machine baseline.

8. **Does trajectory add value?**
   M2 (Spread + Trajectory) achieved held-out Brier of 0.2677 and LOOCV Brier of 0.2774, showing prospective calibration improvement, but remains provisional pending multi-season validation.

9. **Does ensemble geometry add value?**
   M3 (Spread + Geometry) reduced held-out Brier to 0.1850 and LOOCV Brier to 0.2887, indicating spatial elongation and bimodality provide structural failure signals, but remains provisional.

10. **DOES M4 CYCLE-TO-CYCLE INSTABILITY ADD VALUE?**
    **M4 provides valuable DIAGNOSTIC INDICATOR telemetry**. Across 41 cycle revision pairs, mean track revision was 57.65 km (median 51.72 km). There is a statistically significant positive empirical association ($r = +0.4482$) between 12h cycle revision distance and track error. However, direct linear inclusion degraded out-of-event test metrics (Held-Out Brier 0.5186), so M4 is kept as an operational diagnostic rather than an automated predictor.

11. **Does M5 reliability contradiction add value?**
    **Retained as diagnostic machine-learning layer**. Leakage-free M5 achieved LOOCV Brier of 0.2956 (outperforming M0 0.3086 and M1 0.3213) and LOOCV ECE of 0.3766, successfully identifying false-confidence situations where spread was deceptively narrow.

12. **What is the best defensible model?**
    **M0 (Climatology)** is the operational reference baseline. **M1 (Spread-Only)** is the stable primary machine baseline. **M5** serves as the diagnostic overlay for false confidence.

13. **What remains statistically inconclusive?**
    Higher-order feature families (M2, M3, M5, M6) show promising calibration improvements on this 6-storm pilot, but cannot be claimed as statistically proven replacements for simple ensemble spread without multi-year archives.

14. **What are the limitations?**
    - Sample scale: 6 cyclones, 13 forecast cycles, 101 exact leads, 41 cycle revision pairs.
    - Evaluation is strictly on North Indian Ocean tropical cyclone MSLP vortex tracking (not nationwide gridded rainfall).
    - Held-out test event (MICHAUNG) had zero busts, which skews test-event error distributions.

---

## M0 to M6 Ablation Summary Table

| Model | Architecture | Held-Out Brier | Held-Out ECE | LOOCV Brier | LOOCV ECE | Decision |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **M0** | Climatology Baseline | 0.3295 | 0.5597 | 0.3086 | 0.3848 | **RETAINED (Operational Reference)** |
| **M1** | Scalar Ensemble Spread | 0.3302 | 0.5605 | 0.3213 | 0.4277 | **RETAINED (Primary Machine Baseline)** |
| **M2** | Spread + Trajectory | 0.2677 | 0.4637 | 0.2774 | 0.3482 | **PROVISIONAL (Calibration Improvement)** |
| **M3** | + Spatial Geometry | 0.1850 | 0.4172 | 0.2887 | 0.3842 | **PROVISIONAL (Structural Signal)** |
| **M4** | + Cycle-to-Cycle Instability | 0.5186 | 0.7040 | 0.3616 | 0.4708 | **KILLED (Degrades Test Metrics)** |
| **M5** | + Reliability Contradiction | 0.3619 | 0.5818 | 0.2956 | 0.3766 | **RETAINED (Diagnostic Overlay)** |
| **M6** | Combined Candidate | 0.1798 | 0.3818 | 0.2728 | 0.3540 | **PROVISIONAL (Best Held-Out Brier)** |
