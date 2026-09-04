# FORECASTGUARD — SYSTEM ARCHITECTURE

## 1. PURPOSE

ForecastGuard is an AI-based forecast reliability intelligence system for medium-range numerical weather prediction (NWP).

The system does not replace NCMRWF, IMD, or any official forecasting or warning service.

Its purpose is to continuously estimate:

- how vulnerable an existing forecast is to significant failure,
- how that vulnerability evolves with forecast lead time,
- where forecast failure is most likely,
- what type of failure is likely,
- why the system believes reliability is degrading,
- how early the degradation can be detected,
- and whether the current forecast trajectory resembles historical forecast-failure pathways.

Core product principle:

> NWP tells us what may happen. ForecastGuard tells us how much we should trust that forecast.

ForecastGuard is therefore a reliability and decision-support layer over existing NWP forecasts.

---

## 2. SYSTEM BOUNDARY

ForecastGuard operates between forecast generation and operational human decision-making.

It consumes:

- NWP forecasts,
- ensemble forecasts,
- observations and analyses,
- historical forecast-error records,
- atmospheric state information,
- and, where available, forecasts from other NWP centres.

It produces:

- forecast reliability estimates,
- bust probabilities,
- spatial risk/error-prone regions,
- lead-time reliability trajectories,
- failure-type predictions,
- evidence explaining reliability degradation,
- historical analogue information,
- verification results,
- and operational alerts.

ForecastGuard must not:

- replace official forecasts,
- issue independent public warnings,
- claim certainty about atmospheric outcomes,
- fabricate missing observations,
- fabricate forecast skill,
- or represent experimental outputs as operationally validated results.

---

## 3. CORE ARCHITECTURAL PRINCIPLES

### 3.1 Scientific integrity

Every scientific output must be traceable to:

1. a defined input dataset,
2. a reproducible computation,
3. a documented methodology,
4. and an appropriate validation procedure.

The system must never hardcode scientific risk values simply to make the dashboard appear convincing.

If evidence is insufficient, the system must be capable of saying:

> Insufficient evidence.

---

### 3.2 No future-information leakage

At any forecast lead time, ForecastGuard may only use information that would have been available at that point in the historical operational timeline.

For example:

If the system is evaluating D+5 reliability, it must not use:

- D+6 observations,
- D+7 observations,
- later forecast runs,
- verification information generated after D+5,
- or any feature derived from future knowledge.

Future observations are used only for verification and label generation after the prediction point.

---

### 3.3 Complexity must earn its place

The system will not assume that a more complicated model is automatically better.

Every advanced component must be compared against simpler baselines.

Examples:

- persistence versus trajectory modelling,
- ensemble spread versus ensemble geometry,
- simple model disagreement versus multi-model graph dynamics,
- ordinary analogues versus forecast-trajectory analogues,
- current-state models versus historical-pathway models.

If an advanced method does not provide meaningful validated improvement, it should be removed or downgraded to an experimental research component.

---

### 3.4 Reliability is a trajectory

Forecast reliability should not be treated only as a static binary classification.

ForecastGuard should investigate the evolution:

> STABLE → UNCERTAIN → DEGRADING → HIGH RISK → VERIFIED FAILURE

These states are conceptual and must not be treated as scientifically established until supported by validation.

The core scientific question is:

> How early can ForecastGuard reliably detect an upcoming forecast bust?

---

## 4. HIGH-LEVEL SYSTEM ARCHITECTURE

The system is organized as the following pipeline:

REAL NWP FORECASTS
        |
        v
DATA INGESTION
        |
        v
DATA ALIGNMENT + QUALITY CONTROL
        |
        +-------------------+
        |                   |
        v                   v
ENSEMBLE              MULTI-MODEL
INTELLIGENCE          INTELLIGENCE
        |                   |
        +---------+---------+
                  |
                  v
        ATMOSPHERIC STATE
             ANALYSIS
                  |
                  v
       FORECAST TRAJECTORY
              ENGINE
                  |
        +---------+---------+
        |         |         |
        v         v         v
   HISTORICAL    OOD /   ENSEMBLE-
   TRAJECTORY   NOVELTY   BASED
   ANALOGUES    ANALYSIS  FRAGILITY
        |         |         |
        +---------+---------+
                  |
                  v
         CALIBRATED AI
           RISK ENGINE
                  |
        +---------+---------+
        |         |         |
        v         v         v
      WHERE     WHEN     HOW / WHY
        |         |         |
        +---------+---------+
                  |
                  v
       OBSERVATION-BASED
          VERIFICATION
                  |
                  v
         BUST ATLAS /
           AUTOPSY
                  |
                  v
          LEARNING LOOP

The final architecture must allow individual components to be evaluated independently.

---

## 5. MAJOR SYSTEM COMPONENTS

ForecastGuard is divided into the following major components:

1. Forecast Data Ingestion
2. Observation Data Ingestion
3. Data Alignment
4. Quality Control
5. Forecast Verification
6. Forecast Error Representation
7. Ensemble Intelligence
8. Forecast Trajectory Engine
9. Multi-Model Intelligence
10. Atmospheric Regime Analysis
11. Historical Analogue Engine
12. Forecast Failure Pathway Memory
13. OOD / Novelty Analysis
14. Ensemble-Based Fragility Analysis
15. AI Risk Engine
16. Probability Calibration
17. Failure Morphology Prediction
18. Evidence and Explanation Engine
19. Alert and Decision Layer
20. Historical Replay Engine
21. Forecast Autopsy Engine
22. API Layer
23. Database Layer
24. Scientific Storage Layer
25. Frontend Visualization Layer
26. Validation and Experimentation Layer
27. Monitoring and Observability Layer

Each component should have a clear responsibility and should not silently duplicate another component's role.

---

## 6. DATA FLOW

The canonical data flow is:

FORECAST SOURCE
    |
    v
RAW FORECAST
    |
    v
NORMALIZATION
    |
    v
ALIGNED FORECAST
    |
    +----------------------------+
    |                            |
    v                            v
ENSEMBLE FEATURES          SPATIAL FEATURES
    |                            |
    +-------------+--------------+
                  |
                  v
          TRAJECTORY FEATURES
                  |
                  +------------------+
                  |                  |
                  v                  v
        HISTORICAL MEMORY       MODEL COMPARISON
                  |                  |
                  +--------+---------+
                           |
                           v
                    RISK ENGINE
                           |
                           v
                    CALIBRATION
                           |
                           v
                 OPERATIONAL OUTPUT
                           |
                           v
                     VERIFICATION
                           |
                           v
                    FAILURE MEMORY

The same verified historical cases should eventually feed the historical learning and analogue systems.

---

## 7. DATA SOURCE STRATEGY

The primary forecast source for the first implementation is:

> NCMRWF NCUM / NEPS historical forecasts available through TIGGE.

The system should preserve source identity and model metadata.

Where legally and technically available, additional NWP centres may be incorporated for multi-model analysis.

Potential additional forecast sources include:

- ECMWF,
- NCEP,
- UKMO,
- JMA,
- CMA,
- and other authorized forecast sources.

The architecture must not assume that every source has identical:

- resolution,
- forecast cycle,
- ensemble size,
- lead time,
- variables,
- accumulation definitions,
- or model versions.

Those differences must remain explicit in the metadata.

---

## 8. PRIMARY OBSERVATION / VERIFICATION STRATEGY

The first major verification target is precipitation over India.

The primary verification workflow should use an appropriate IMD/NCMRWF precipitation analysis or equivalent authorized observation product.

The system must preserve:

- observation source,
- observation timestamp,
- accumulation window,
- spatial resolution,
- units,
- quality flags,
- and preprocessing history.

Forecast precipitation must be compared against observations only after exact temporal and spatial alignment.

The architecture must support additional verification variables later, including temperature and other event-relevant meteorological quantities.

---

## 9. DATA PROVENANCE

Every important scientific dataset must have provenance.

At minimum, provenance should identify:

- source,
- dataset name,
- provider,
- retrieval time,
- original file/reference,
- model,
- model version where available,
- forecast initialization,
- forecast type,
- variable,
- level,
- member,
- valid time,
- lead time,
- spatial domain,
- units,
- preprocessing version,
- and software/pipeline version.

Scientific results must be reproducible from stored provenance.

No manually edited forecast or observation values should become the authoritative source of truth.

---

## 10. RAW DATA PRESERVATION

Original forecast files should be treated as immutable source artifacts.

For NWP GRIB2 data, the raw files should be preserved before scientific transformation.

Derived datasets may be regenerated from raw data.

The system should therefore follow:

RAW DATA
    ↓
PARSED DATA
    ↓
ALIGNED DATA
    ↓
DERIVED FEATURES
    ↓
MODEL OUTPUT
    ↓
VERIFICATION

Raw source data must never be overwritten by processed data.
# CHUNK 2 — FORECAST DATA INGESTION AND DATA ALIGNMENT

## 11. FORECAST DATA INGESTION

The Forecast Data Ingestion subsystem is responsible for acquiring forecast data from approved sources and converting it into a consistent internal representation.

The ingestion layer must support:

- NCMRWF / TIGGE forecasts,
- ensemble forecasts,
- deterministic forecasts where available,
- multiple forecast cycles,
- multiple lead times,
- multiple meteorological variables,
- multiple spatial resolutions,
- and multiple NWP centres.

The ingestion system must distinguish between:

- source data,
- parsed data,
- normalized data,
- and derived data.

No scientific feature engineering should occur inside the raw-download layer.

---

## 12. TIGGE / NCMRWF INGESTION

The first implementation should target NCMRWF forecasts represented in TIGGE.

The NCMRWF TIGGE centre identifier is:

    dems

The initial implementation should focus on a small, controlled subset of the archive before scaling.

Initial target:

    Centre: dems
    Variable: tp
    Forecast type: ensemble / perturbed forecast
    Cycle: 00 UTC
    Lead times: D+1 through D+10
    Domain: India-focused
    Period: one historical month

The purpose of the initial dataset is pipeline validation.

It is not sufficient evidence for final scientific conclusions.

---

## 13. FORECAST CYCLE IDENTIFICATION

Every forecast must retain its initialization time.

The system must distinguish between:

- initialization time,
- forecast valid time,
- forecast lead time,
- accumulation start,
- accumulation end.

For example, a forecast initialized at time T and valid at T + 120 hours must retain both:

    initialization_time = T
    valid_time = T + 120 hours

The system must never infer lead time solely from a filename if reliable GRIB metadata is available.

---

## 14. ENSEMBLE MEMBER HANDLING

Ensemble members must remain individually identifiable during ingestion.

The system must preserve:

- control member identity where applicable,
- perturbed-member identity,
- member number,
- forecast initialization,
- valid time,
- variable,
- and lead time.

The ingestion layer must never silently collapse ensemble members into an ensemble mean.

Individual members are required for later analysis of:

- spread,
- divergence,
- clustering,
- branching,
- multimodality,
- ensemble coherence,
- and ensemble-based fragility.

---

## 15. GRIB METADATA EXTRACTION

When GRIB2 data are ingested, the system should inspect and preserve relevant metadata.

Important metadata include:

- edition,
- centre,
- sub-centre,
- data type,
- forecast type,
- type of level,
- short name,
- parameter identifier,
- step,
- start step,
- end step,
- initialization date,
- initialization time,
- forecast member,
- units,
- grid type,
- grid dimensions,
- latitude information,
- longitude information,
- missing-value representation.

The ingestion pipeline should expose this metadata to the quality-control system.

---

## 16. VARIABLE SEMANTICS

ForecastGuard must treat meteorological variables according to their physical definitions.

The system must not assume that two variables with similar names have identical meanings.

For precipitation in particular, the system must explicitly handle:

- accumulated versus instantaneous quantities,
- accumulation start time,
- accumulation end time,
- forecast step,
- units,
- and temporal aggregation.

For example, total precipitation may be represented as an accumulated quantity.

The implementation must verify the actual source semantics before calculating forecast totals.

---

## 17. TEMPORAL NORMALIZATION

All forecast timestamps should use a consistent internal representation.

Recommended internal standard:

    UTC

The system must preserve the original source timestamp and timezone interpretation where relevant.

Each forecast record should make it possible to determine:

    initialization time
    valid time
    lead time
    accumulation window

The temporal normalization layer must prevent:

- duplicate valid times,
- accidental cycle mixing,
- incorrect lead-time calculations,
- and observation-window mismatches.

---

## 18. SPATIAL NORMALIZATION

Different forecast sources may use different:

- grids,
- resolutions,
- map projections,
- longitude conventions,
- latitude ordering,
- and spatial extents.

ForecastGuard must therefore maintain explicit grid metadata.

Before comparison, fields must be transformed onto an agreed verification grid.

For the initial precipitation verification system, the verification grid should follow the selected IMD/NCMRWF observation product.

The regridding method must be documented and reproducible.

---

## 19. INDIA DOMAIN

The initial system should focus computationally on the India-relevant domain.

However, the ingestion layer should preserve enough surrounding atmospheric information to support later analysis of systems affecting India.

The system should therefore distinguish between:

    computational verification domain

and:

    atmospheric context domain

This distinction is important because weather systems influencing India may originate or evolve outside the final verification region.

---

## 20. DATA QUALITY CONTROL PIPELINE

Every forecast dataset must pass quality control before becoming available to downstream scientific modules.

Conceptual pipeline:

    RAW FILE
       |
       v
    FILE CHECK
       |
       v
    METADATA CHECK
       |
       v
    TEMPORAL CHECK
       |
       v
    SPATIAL CHECK
       |
       v
    VALUE CHECK
       |
       v
    ENSEMBLE CHECK
       |
       v
    DUPLICATE CHECK
       |
       v
    QC STATUS

Each record should receive an explicit quality status.

Possible statuses:

    VALID
    WARNING
    INVALID
    MISSING

Invalid data must not silently enter model training.

---

## 21. FORECAST QUALITY-CONTROL CHECKS

At minimum, the QC system should verify:

    [ ] File can be opened
    [ ] Expected forecast initialization exists
    [ ] Expected forecast cycle exists
    [ ] Expected variable exists
    [ ] Expected lead times exist
    [ ] Expected members exist
    [ ] Spatial coverage is valid
    [ ] Coordinates are valid
    [ ] Units are recognized
    [ ] Accumulation semantics are recognized
    [ ] Missing values are identified
    [ ] Duplicate records are identified
    [ ] Metadata are internally consistent

The QC result should be logged.

---

## 22. OBSERVATION INGESTION

Observation and analysis products must enter ForecastGuard through a separate ingestion pipeline.

The observation pipeline must preserve:

- source,
- timestamp,
- variable,
- accumulation window,
- grid,
- units,
- quality flags,
- and source provenance.

Observation data must not be modified merely to make a forecast appear better.

Any preprocessing must be deterministic and documented.

---

## 23. FORECAST–OBSERVATION TEMPORAL ALIGNMENT

Temporal alignment is one of the most important scientific safeguards in ForecastGuard.

A forecast may only be verified against an observation representing the same physical period.

For precipitation, the system must explicitly compare:

    forecast accumulation window

against:

    observation accumulation window

The system must not compare:

    forecast valid-at time

with:

    observation accumulated-over-a-different-window

unless a scientifically justified transformation has been applied.

All temporal transformations must be recorded.

---

## 24. FORECAST–OBSERVATION SPATIAL ALIGNMENT

Forecast and observation fields may exist on different grids.

Before calculating spatial verification metrics, the system must establish a common verification grid.

The pipeline should explicitly record:

- original forecast grid,
- observation grid,
- regridding method,
- target grid,
- interpolation/remapping configuration,
- land-mask treatment where applicable.

The same documented procedure must be used consistently during training and evaluation.

---

## 25. MISSING DATA POLICY

Missing values must never be silently converted to zero.

The system must distinguish between:

    actual zero

and:

    missing observation / missing forecast

Missing data handling must be variable-specific where necessary.

Each verification result should retain sufficient information to determine whether missing data influenced the metric.

---

## 26. DUPLICATE DATA POLICY

Duplicate forecast records must be detected before downstream processing.

Duplicates may arise from:

- repeated downloads,
- overlapping archive files,
- multiple ingestion attempts,
- duplicated GRIB messages,
- or inconsistent source packaging.

A deterministic record identity should be constructed using relevant metadata such as:

    source
    model
    initialization
    variable
    level
    member
    valid time
    step

Duplicate records must not be counted twice.

---

## 27. MODEL VERSION TRACKING

ForecastGuard must preserve model-version information whenever available.

Model upgrades can change:

- forecast characteristics,
- error distributions,
- ensemble behaviour,
- spatial biases,
- and apparent model skill.

Therefore, historical verification and machine-learning experiments should retain model-era metadata.

The system must not blindly treat all historical forecasts as statistically identical.

---

## 28. DATASET VERSIONING

Every derived scientific dataset must have a reproducible version.

A dataset version should identify:

- source dataset,
- extraction period,
- variables,
- domain,
- grid,
- preprocessing version,
- alignment version,
- QC version,
- and generation timestamp or pipeline version.

Model experiments must reference the dataset version used.

---

## 29. IMMUTABLE RAW / REPRODUCIBLE DERIVED DATA

The architecture follows this rule:

    RAW DATA
        |
        v
    PARSING
        |
        v
    NORMALIZATION
        |
        v
    ALIGNMENT
        |
        v
    FEATURES
        |
        v
    MODEL
        |
        v
    OUTPUT
        |
        v
    VERIFICATION

Raw source data remain immutable.

Derived data may be regenerated.

No downstream module should modify raw source files.

---

## 30. DATA VALIDATION BEFORE SCIENTIFIC USE

A dataset is not considered scientifically usable merely because it can be loaded successfully.

Before training or evaluation, ForecastGuard must confirm:

- temporal correctness,
- spatial correctness,
- unit correctness,
- accumulation correctness,
- member correctness,
- observation matching,
- missing-value handling,
- and absence of obvious leakage.

The system should generate a machine-readable dataset validation report.

A dataset that fails critical validation must be blocked from scientific model training.# CHUNK 3 — VERIFICATION ENGINE AND FORECAST ERROR

## 31. VERIFICATION ENGINE

The Verification Engine converts aligned forecasts and observations into scientifically defined forecast-error measurements.

Its purpose is to answer:

> How wrong was the forecast?

and eventually:

> Was the forecast wrong enough to be considered a meaningful bust?

The Verification Engine must operate independently from the AI risk model.

This separation is critical.

The AI model predicts future reliability.

The Verification Engine determines what actually happened.

---

## 32. VERIFICATION PIPELINE

The canonical verification pipeline is:

    FORECAST
        |
        v
    OBSERVATION
        |
        v
    TEMPORAL ALIGNMENT
        |
        v
    SPATIAL ALIGNMENT
        |
        v
    QUALITY CONTROL
        |
        v
    ERROR CALCULATION
        |
        v
    ERROR NORMALIZATION
        |
        v
    EVENT / STRUCTURAL ANALYSIS
        |
        v
    BUST SEVERITY
        |
        v
    FAILURE FINGERPRINT

Verification must be reproducible from the stored forecast and observation records.

---

## 33. VERIFICATION TARGETS

The first verification target is precipitation.

The architecture must support multiple verification dimensions rather than relying on one metric.

Potential future verification variables include:

- precipitation,
- maximum temperature,
- minimum temperature,
- wind,
- pressure,
- geopotential height,
- and event-specific variables.

The same verification framework should be extensible to additional variables.

---

## 34. CONTINUOUS ERROR TARGET

ForecastGuard should maintain continuous error measures before converting them into categorical bust labels.

Examples include:

- MAE,
- RMSE,
- bias,
- normalized MAE,
- normalized RMSE.

Continuous error is important because an arbitrary binary label can discard useful information.

The machine-learning system should therefore have access to the underlying continuous error representation when scientifically appropriate.

---

## 35. SPATIAL ERROR

Weather forecast failure is often spatially structured.

The verification system should therefore retain spatial error fields.

For a forecast field F and observation field O:

    E(x,y) = F(x,y) - O(x,y)

The system should support spatial summaries such as:

- mean absolute error,
- root mean square error,
- bias,
- percentile error,
- regional error,
- spatial extent of significant error.

Spatial error fields should remain available for visualization and downstream analysis.

---

## 36. ERROR MAGNITUDE

Error magnitude represents how far the forecast is from the verifying observation.

The system should calculate appropriate magnitude metrics according to the variable.

For precipitation, for example:

    absolute_error = |forecast - observation|

and:

    squared_error = (forecast - observation)^2

These basic quantities may then be aggregated into:

- MAE,
- RMSE,
- regional statistics,
- lead-time statistics,
- and event-specific statistics.

The choice of metric must be documented.

---

## 37. BIAS

Bias measures systematic directional error.

Conceptually:

    bias = mean(forecast - observation)

Positive and negative biases must not be treated as equivalent operationally in every context.

The verification system should retain signed bias as well as absolute error.

Bias should be analyzed by:

- region,
- season,
- lead time,
- variable,
- forecast cycle,
- and model version where appropriate.

---

## 38. SPATIAL DISPLACEMENT

A forecast can have the correct general event magnitude but place it in the wrong location.

Therefore ForecastGuard should investigate spatial displacement separately from simple pointwise error.

Potential future metrics may include:

- centroid displacement,
- object displacement,
- distance-based precipitation verification,
- neighborhood methods,
- spatial correlation,
- structure-based metrics.

These methods should be introduced only when sufficient event data and validation are available.

---

## 39. TIMING ERROR

Forecast failure may occur because an event is predicted too early or too late.

The verification system should therefore preserve event timing information where the event definition supports it.

Potential timing measures include:

- onset difference,
- peak-time difference,
- cessation difference,
- duration difference.

Timing errors should not be inferred when the observation/forecast definition does not support a meaningful event boundary.

---

## 40. EVENT DETECTION

For event-based verification, ForecastGuard should support a configurable event definition.

Possible event definitions include:

- rainfall exceeding a threshold,
- extreme rainfall,
- spatially coherent rainfall,
- cyclone-related precipitation,
- heat events,
- high-wind events.

Thresholds must be defined independently of the prediction model.

Event definitions must be documented and versioned.

---

## 41. CONTINGENCY TABLE

For binary event verification, ForecastGuard should support:

    HIT
    MISS
    FALSE ALARM
    CORRECT NEGATIVE

These can be used to calculate appropriate event metrics.

Potential metrics include:

- Probability of Detection,
- False Alarm Ratio,
- Critical Success Index,
- Frequency Bias,
- equitable skill measures where appropriate.

The system must not select whichever metric produces the most favorable result.

Metric choice must follow the scientific question.

---

## 42. CLIMATOLOGY NORMALIZATION

A large raw error is not automatically unusual.

Forecast difficulty depends on:

- region,
- season,
- lead time,
- weather regime,
- and climatological variability.

ForecastGuard should therefore maintain appropriate historical reference distributions.

For example:

    normalized_error =
        observed_error /
        historical_reference_error

The exact normalization method must be selected experimentally and documented.

---

## 43. LEAD-TIME DEPENDENCE

Forecast error naturally changes with lead time.

Therefore the verification system must not apply a single universal error threshold blindly across:

    D+1
    D+2
    ...
    D+10

Error statistics should be analyzed conditionally on lead time.

Bust thresholds, if used, should therefore be justified with respect to:

- lead time,
- region,
- season,
- variable,
- and forecast population.

---

## 44. REGIONAL DEPENDENCE

Forecast error characteristics may differ substantially across India.

The verification system should support regional aggregation.

Potential regions may include:

- Northwest India,
- North India,
- Central India,
- Northeast India,
- West Coast,
- East Coast,
- South Peninsula,
- Himalayan regions.

The final regional definitions must be documented and consistently applied.

The system should also retain grid-level information rather than reducing everything to regional averages.

---

## 45. BUST DEFINITION

Forecast bust must not be defined as:

    error > arbitrary number

unless that threshold has a scientific justification.

Instead, ForecastGuard should construct a multi-dimensional bust definition using combinations of:

- error magnitude,
- climatology-normalized error,
- spatial displacement,
- timing error,
- event miss,
- false alarm,
- structural error.

The final bust definition must be:

- explicit,
- reproducible,
- versioned,
- and validated.

---

## 46. BUST SEVERITY

The system should support severity categories.

Initial conceptual levels:

    NORMAL
    DEGRADED
    MAJOR
    SEVERE

These are labels, not predefined scientific thresholds.

Thresholds must be derived from the verification distribution and operational/scientific requirements.

The threshold-generation procedure must be stored as part of the experiment configuration.

---

## 47. MULTI-DIMENSIONAL FAILURE REPRESENTATION

A forecast failure should be represented as a vector rather than a single scalar.

Conceptually:

    Failure =
    {
        magnitude,
        location,
        timing,
        structure,
        event_status,
        severity
    }

This representation allows ForecastGuard to distinguish different types of failure.

For example:

    correct location + wrong intensity

is different from:

    wrong location + correct intensity

and different again from:

    missed event entirely.

---

## 48. FAILURE FINGERPRINT

Every verified case should generate a failure fingerprint.

The fingerprint should describe:

    WHERE
    WHEN
    HOW MUCH
    WHAT STRUCTURE
    WHAT EVENT
    HOW SEVERE

Example conceptual representation:

    location:
        Central India

    timing:
        event delayed

    magnitude:
        large positive error

    structure:
        precipitation maximum displaced

    event:
        heavy-rain event missed

    severity:
        MAJOR

The actual values must always come from verification.

No example values should be hardcoded into production outputs.

---

## 49. FORECAST FAILURE MORPHOLOGY

ForecastGuard should eventually investigate whether the system can predict the type of future failure before verification.

Define a failure morphology:

    M =
    {
        location,
        timing,
        intensity,
        structure,
        event
    }

The predictive task becomes:

    P(M_future | information_available_now)

The prediction must use only information available before the failure is verified.

This module should be evaluated separately from the basic bust-probability model.

---

## 50. VERIFICATION DATASET

Each verified forecast case should retain:

    forecast_run
    initialization_time
    valid_time
    lead_time
    variable
    region
    forecast_statistics
    observation_statistics
    error_metrics
    event_metrics
    spatial_metrics
    severity
    failure_fingerprint

This dataset becomes the foundation for:

- baseline models,
- AI training,
- historical analogues,
- failure pathway memory,
- calibration,
- and scientific evaluation.

---

## 51. VERIFICATION INDEPENDENCE

The verification pipeline must remain independent from the model that predicts bust risk.

The model must not be allowed to modify the definition of the observed outcome merely to improve its own performance.

Correct separation:

    FORECAST
        |
        +--------------------+
        |                    |
        v                    v
    PREDICTION           VERIFICATION
        |                    |
        v                    v
    RISK OUTPUT         TRUE OUTCOME
        |                    |
        +---------+----------+
                  |
                  v
              EVALUATION

This prevents circular evaluation.

---

## 52. VERIFICATION QUALITY FLAGS

Every verification result should have a quality status.

Possible states:

    VERIFIED
    PARTIALLY_VERIFIED
    INSUFFICIENT_DATA
    INVALID

A prediction should not be evaluated against an observation pair marked invalid.

Partial verification should be explicitly reported rather than silently treated as complete.

---

## 53. REGIONAL AND TEMPORAL VERIFICATION REPORTS

The system must support verification summaries by:

- lead time,
- region,
- season,
- forecast cycle,
- model,
- model version,
- event class,
- and severity.

This allows the team to determine whether ForecastGuard works uniformly or only under specific conditions.

---

## 54. FORECAST VERIFICATION ATLAS

ForecastGuard should maintain a Forecast Verification Atlas.

The atlas should provide:

- D+1 through D+10 error statistics,
- spatial error maps,
- bias maps,
- regional statistics,
- event verification,
- bust-severity distributions,
- failure fingerprints,
- seasonal behaviour,
- and model-version comparisons.

This atlas is a scientific foundation for the AI system.

It should exist even if the advanced AI components are later removed.

---

## 55. VERIFICATION AS THE GROUND TRUTH LAYER

The verification system represents what actually happened.

Therefore:

    Forecast model
        =
    prediction

while:

    Verification Engine
        =
    observed outcome assessment

The AI reliability system must ultimately be evaluated against this verification layer.

No dashboard visualization, confidence score, or explanation can substitute for actual verification.
# CHUNK 4 — ENSEMBLE INTELLIGENCE AND FORECAST TRAJECTORY ENGINE

## 56. ENSEMBLE INTELLIGENCE

The Ensemble Intelligence subsystem analyzes the internal structure and evolution of the NWP ensemble.

The objective is not simply to calculate ensemble spread.

ForecastGuard should investigate whether the way ensemble members evolve contains information about future forecast failure.

The subsystem should analyze:

- ensemble mean,
- ensemble spread,
- spread growth,
- spread acceleration,
- member divergence,
- member similarity,
- clustering,
- branch emergence,
- branch persistence,
- multimodality,
- ensemble coherence,
- and mean-versus-member relationships.

---

## 57. ENSEMBLE MEAN

For an ensemble containing N members:

    ensemble_mean =
        (1/N) * sum(member_i)

The ensemble mean provides a central estimate of the forecast distribution.

It should be stored independently from individual members.

The ensemble mean must never replace the underlying members because later analysis requires the full ensemble geometry.

---

## 58. ENSEMBLE SPREAD

Ensemble spread represents dispersion among ensemble members.

A basic representation is:

    spread =
        standard_deviation(member_values)

Spread should be calculated conditionally on:

- lead time,
- location,
- variable,
- forecast cycle,
- and ensemble population.

ForecastGuard must not assume that high spread automatically means high forecast error.

The relationship between spread and actual error must be measured empirically.

---

## 59. SPREAD GROWTH

ForecastGuard should measure how ensemble spread changes with lead time.

Conceptually:

    spread_growth(t) =
        spread(t) - spread(t-1)

Alternative normalized formulations may also be tested.

The purpose is to identify whether rapidly increasing uncertainty is associated with subsequent forecast failure.

---

## 60. SPREAD ACCELERATION

The system should investigate second-order spread behaviour.

Conceptually:

    spread_acceleration(t) =
        spread_growth(t) - spread_growth(t-1)

This may identify periods where ensemble uncertainty is increasing unusually rapidly.

It is an experimental feature and must be validated against simpler spread and spread-growth baselines.

---

## 61. MEMBER DIVERGENCE

Individual ensemble members may progressively separate as lead time increases.

ForecastGuard should quantify member divergence using appropriate distance measures.

Potential representations include:

- pairwise Euclidean distance,
- normalized field distance,
- spatial correlation distance,
- distributional distance.

The choice of distance must depend on the variable and spatial representation.

---

## 62. MEMBER CLUSTERING

Ensemble members may form multiple internally coherent groups.

ForecastGuard should investigate clustering using validated methods such as:

- hierarchical clustering,
- k-means,
- density-based clustering,
- Gaussian mixture models,
- or other appropriate approaches.

The system must not assume a fixed number of clusters.

Cluster count and stability should be evaluated.

---

## 63. ENSEMBLE BRANCHING

A possible early warning signal is the emergence of distinct forecast branches.

The system should investigate:

    initial coherence
          |
          v
    increasing divergence
          |
          v
    distinct member groups
          |
          v
    persistent branches

Branch emergence should be defined quantitatively.

A temporary split that quickly reconverges should not automatically be treated as meaningful branching.

---

## 64. BRANCH PERSISTENCE

A branch is potentially more informative when it persists across successive forecast lead times.

Therefore the system should distinguish:

    transient divergence

from:

    persistent divergence

Branch persistence can be represented using:

- cluster membership stability,
- inter-cluster distance,
- branch duration,
- and transition probabilities.

These features must be validated against later forecast error.

---

## 65. MULTIMODALITY

Ensemble distributions may contain multiple likely outcomes.

ForecastGuard should investigate whether multimodal distributions contain predictive information beyond standard deviation.

Potential indicators include:

- number of statistically meaningful modes,
- separation between modes,
- relative mode population,
- mode persistence,
- entropy,
- mixture-model likelihood.

Multimodality should only be retained if it improves validated prediction.

---

## 66. ENSEMBLE COHERENCE

Ensemble coherence measures how consistently members support a common forecast evolution.

Potential features include:

- pairwise similarity,
- cluster concentration,
- dominant-cluster fraction,
- trajectory agreement,
- spatial coherence.

The system should distinguish:

    high uncertainty

from:

    multiple coherent alternative scenarios.

These are not necessarily equivalent.

---

## 67. MEAN-VERSUS-MEMBER ANALYSIS

The ensemble mean may conceal important structure.

ForecastGuard should compare:

- ensemble mean,
- control member,
- individual members,
- dominant clusters,
- minority clusters.

This can help determine whether the mean represents a physically meaningful consensus or is averaging across fundamentally different scenarios.

---

## 68. ENSEMBLE GEOMETRY

ForecastGuard should treat the ensemble as a geometric object rather than only a collection of scalar values.

The system may investigate:

    centre
    spread
    orientation
    clustering
    branching
    separation
    persistence

The objective is to determine whether ensemble geometry provides information about future forecast failure beyond conventional spread.

---

## 69. ENSEMBLE BASELINE

Before using advanced ensemble geometry, establish a simple baseline.

Minimum baseline:

    ensemble spread

Then compare:

    spread

against:

    spread + spread growth

and then:

    spread + spread growth + clustering

and then:

    ensemble geometry

Only retain advanced geometry if it provides meaningful improvement.

---

## 70. FORECAST TRAJECTORY ENGINE

The Forecast Trajectory Engine represents forecast evolution through time.

Instead of examining only:

    current forecast state

the system should examine:

    forecast history

and:

    forecast evolution

A conceptual forecast trajectory is:

    X(t-2)
      |
      v
    X(t-1)
      |
      v
    X(t)
      |
      v
    X(t+1)
      |
      v
    X(t+2)

where X represents a forecast-state representation.

---

## 71. RUN-TO-RUN EVOLUTION

ForecastGuard should compare successive forecast initialization cycles.

For a fixed target valid time:

    Forecast Run 1
          |
          v
    Forecast Run 2
          |
          v
    Forecast Run 3
          |
          v
    Forecast Run 4

The system should quantify how the forecast changes as new initialization cycles become available.

Potential features include:

- field difference,
- normalized field difference,
- spatial displacement,
- precipitation change,
- event probability change,
- ensemble distribution change.

---

## 72. RUN-TO-RUN PERSISTENCE

The system must explicitly test persistence because persistence of forecast risk can itself be predictive.

For a target event:

    risk(t)
       |
       v
    risk(t+1)
       |
       v
    risk(t+2)

Potential persistence features include:

- consecutive risk direction,
- consecutive high-risk cycles,
- duration above threshold,
- change in predicted intensity,
- change in predicted location.

The trajectory model must prove that it adds information beyond simple persistence.

---

## 73. FORECAST JUMPINESS

ForecastGuard should measure forecast instability between successive runs.

Potential measures include:

    jump(t) =
        distance(F_t, F_(t-1))

and:

    jump_change(t) =
        jump(t) - jump(t-1)

Jumpiness must not automatically be interpreted as evidence of impending failure.

The system must test whether jumpiness is predictive within the target domain and lead times.

---

## 74. TRAJECTORY REPRESENTATION

A forecast trajectory may include multiple dimensions:

    atmospheric state
    ensemble state
    spatial forecast
    event characteristics
    model-relative position
    uncertainty characteristics

The system should support both:

1. engineered trajectory features,
2. learned trajectory representations.

The simpler representation should be evaluated first.

---

## 75. TRAJECTORY MEMORY HYPOTHESIS

ForecastGuard should investigate whether two forecasts with similar current states can have different future reliability because their histories differ.

Conceptually:

    P(B | X_t, H_A)
        !=
    P(B | X_t, H_B)

where:

    X_t = current forecast state
    H   = previous forecast trajectory
    B   = future forecast bust

If historical trajectory provides predictive information beyond the current state, the result supports path dependence.

---

## 76. SNAPSHOT VERSUS TRAJECTORY EXPERIMENT

The system should explicitly compare:

    Model A:
    current snapshot only

against:

    Model B:
    current snapshot + persistence

against:

    Model C:
    current snapshot + run-to-run evolution

against:

    Model D:
    full trajectory representation

This experiment is essential for determining whether trajectory analysis genuinely contributes scientific value.

---

## 77. TRAJECTORY FEATURES

Candidate trajectory features include:

    run_to_run_distance
    run_to_run_distance_trend
    forecast_persistence
    forecast_jumpiness
    jumpiness_trend
    ensemble_spread
    spread_growth
    spread_acceleration
    cluster_count
    cluster_stability
    branch_strength
    branch_persistence
    model_relative_distance
    model_relative_distance_change

Features must be evaluated individually and in controlled combinations.

---

## 78. TRAJECTORY WINDOWS

The system should support configurable historical windows.

Examples:

    last 2 forecast cycles
    last 3 forecast cycles
    last 5 forecast cycles
    full available forecast trajectory

Window length must be treated as an experimental parameter.

The system must avoid using a trajectory window that would not have been available at the prediction time.

---

## 79. TRAJECTORY NORMALIZATION

Trajectory distances should account for natural differences between:

- variables,
- spatial scales,
- regions,
- seasons,
- lead times,
- and climatological variability.

Raw numerical differences should not automatically be interpreted as meaningful forecast instability.

Normalization strategies must be validated.

---

## 80. TRAJECTORY CHANGE-POINT ANALYSIS

ForecastGuard may investigate whether forecast behaviour undergoes a statistically meaningful transition.

Potential methods include:

- rolling statistics,
- cumulative change detection,
- Bayesian change-point methods,
- hidden-state models.

The system should not assume that every change point corresponds to forecast degradation.

The relationship must be empirically tested.

---

## 81. FORECAST RELIABILITY STATES

The trajectory engine may investigate whether forecast cases naturally pass through recurring reliability states.

Conceptual states:

    STABLE
       |
       v
    UNCERTAIN
       |
       v
    DEGRADING
       |
       v
    HIGH RISK
       |
       v
    VERIFIED FAILURE

These states must be discovered or validated rather than hardcoded as scientific truth.

Possible approaches include:

- Hidden Markov Models,
- clustering,
- change-point detection,
- trajectory embedding,
- survival/hazard modelling.

---

## 82. FAILURE TRANSITION

The system should distinguish between:

    forecast becomes wrong

and:

    forecast becomes predictably vulnerable to becoming wrong

The latter is the operational target.

Define:

    T_alert =
        first time the system issues an actionable warning

and:

    T_failure =
        time the forecast is verified as a bust

Then:

    warning_lead_time =
        T_failure - T_alert

The system should maximize useful warning lead time while controlling false alarms.

---

## 83. TWO-DIMENSIONAL FORECAST EVOLUTION

ForecastGuard should separately analyze:

### Dimension A — Forecast-cycle evolution

How successive forecast runs change.

### Dimension B — Ensemble-member evolution

How members within one forecast cycle diverge or converge.

These dimensions should be analyzed separately before being fused.

The system should investigate whether their interaction provides additional information.

---

## 84. TRAJECTORY OUTPUT

The Forecast Trajectory Engine should expose machine-readable outputs including:

    trajectory_features
    trajectory_embedding
    persistence_metrics
    jumpiness_metrics
    ensemble_geometry_metrics
    state_transition_metrics
    trajectory_quality

These outputs feed:

- historical analogue retrieval,
- AI risk prediction,
- explanation generation,
- replay,
- and scientific evaluation.

---

## 85. TRAJECTORY KILL TESTS

The trajectory subsystem must be removed or simplified if:

1. trajectory does not beat snapshot models;
2. trajectory only reproduces persistence;
3. trajectory improves AUC but not useful warning lead time;
4. trajectory improvement disappears under chronological validation;
5. trajectory features fail across seasons or regions;
6. trajectory performance depends on information unavailable operationally.

A complex trajectory representation is not justified merely because it produces a higher training score.

The final system should retain the simplest trajectory representation that provides reproducible predictive value.
# CHUNK 5 — MULTI-MODEL INTELLIGENCE, ATMOSPHERIC REGIMES AND HISTORICAL MEMORY

## 86. MULTI-MODEL INTELLIGENCE

The Multi-Model Intelligence subsystem compares forecasts from multiple NWP systems.

The objective is not simply to calculate an average across models.

The system should investigate:

- whether models agree,
- whether disagreement is increasing,
- whether one model is becoming an outlier,
- whether disagreement is broad across the atmospheric system,
- and whether disagreement is specifically associated with future NCMRWF forecast failure.

---

## 87. MODEL COMPARISON

For a common forecast target, the system should align available models by:

    initialization time
    valid time
    lead time
    variable
    spatial grid
    units
    accumulation window

Only scientifically comparable fields should be directly compared.

If exact alignment is impossible, the limitation must be recorded.

---

## 88. MODEL RELATIVE DISTANCE

ForecastGuard should calculate a model-relative distance:

    D_t = d(F_NCMRWF,t, F_peer,t)

where:

    F_NCMRWF,t =
        NCMRWF forecast representation

and:

    F_peer,t =
        another model forecast representation.

The distance function may use:

- normalized field distance,
- spatial correlation,
- distributional distance,
- event-location distance,
- or other validated measures.

---

## 89. MODEL RELATIVE DIVERGENCE

The system should also measure how model disagreement changes with time.

Conceptually:

    DeltaD_t =
        D_t - D_(t-1)

A persistent increase in disagreement may be more informative than a single large disagreement.

This must be tested empirically.

---

## 90. MULTI-MODEL GRAPH

ForecastGuard may represent NWP systems as a graph.

Conceptually:

    MODEL A -------- MODEL B
       \              /
        \            /
         \          /
          MODEL C
             |
          MODEL D

Where:

    node =
        NWP model

and:

    edge =
        forecast similarity / disagreement.

The graph may be weighted using validated forecast-distance measures.

---

## 91. GRAPH DYNAMICS

The system should investigate whether the structure of the model graph changes before forecast failure.

Potential indicators include:

- increasing graph fragmentation,
- persistent model separation,
- NCMRWF becoming an outlier,
- peer-group formation,
- changing centrality,
- rapid edge-weight changes.

These are experimental features.

They must be compared against simpler model-disagreement baselines.

---

## 92. BROAD PREDICTABILITY BREAKDOWN

Multi-model disagreement should not automatically be interpreted as NCMRWF failure.

ForecastGuard should distinguish:

    broad model disagreement

from:

    NCMRWF-specific disagreement.

If most models diverge in similar ways, the atmosphere may simply be difficult to predict.

If NCMRWF becomes a persistent outlier while peers remain relatively coherent, the signal may be more specifically related to NCMRWF forecast reliability.

This distinction is a major purpose of the multi-model subsystem.

---

## 93. FALSE CONSENSUS

ForecastGuard should investigate:

> High model agreement + high eventual error.

This represents a possible false-consensus regime.

The system should identify cases where:

    model disagreement is low

but:

    verified error is high.

This must be compared against climatology and ensemble-based baselines.

If the phenomenon is weak or not useful, the module should not be emphasized.

---

## 94. MODEL VERSION AWARENESS

Multi-model comparisons must account for changes in model configuration.

The system should retain:

- model identity,
- model version,
- forecast cycle,
- upgrade period where known.

A model upgrade may change its forecast distribution and therefore alter model-distance statistics.

---

## 95. MULTI-MODEL BASELINE

Before implementing graph-based methods, establish simpler baselines.

Minimum progression:

    single-model baseline

then:

    model disagreement

then:

    model disagreement trend

then:

    graph representation

The graph representation should only be retained if it provides measurable improvement.

---

# 96. ATMOSPHERIC STATE ANALYSIS

ForecastGuard should analyze the atmospheric state surrounding the forecast.

The purpose is to determine whether forecast reliability changes under particular atmospheric regimes.

Potential atmospheric variables include:

- 500 hPa geopotential height,
- mean sea-level pressure,
- winds,
- vorticity,
- divergence,
- moisture,
- moisture convergence,
- CAPE,
- vertical shear,
- temperature,
- surface pressure,
- sea-surface temperature where available.

The exact feature set must be determined by data availability and validation.

---

## 97. ATMOSPHERIC STATE REPRESENTATION

Atmospheric state should be represented in a form suitable for:

- machine learning,
- similarity search,
- regime detection,
- OOD analysis,
- and visualization.

Possible representations include:

    engineered physical features

and:

    learned low-dimensional embeddings.

The system should establish a simple physical-feature baseline before relying on learned embeddings.

---

## 98. ATMOSPHERIC REGIME DETECTION

ForecastGuard should investigate whether forecasts behave differently under recurring atmospheric regimes.

Possible regimes may include:

- stable large-scale flow,
- monsoon active conditions,
- monsoon break conditions,
- cyclone-influenced conditions,
- western-disturbance situations,
- rapidly evolving synoptic systems,
- extreme heat regimes,
- strong moisture-convergence regimes.

These are examples rather than a fixed taxonomy.

The final regime structure must be derived or validated from data.

---

## 99. REGIME TRANSITIONS

A stable atmospheric regime may transition into a rapidly evolving state.

ForecastGuard should therefore examine:

    regime A
       |
       v
    transition
       |
       v
    regime B

Potential features include:

- rate of state change,
- circulation change,
- moisture change,
- pressure evolution,
- vorticity evolution,
- ensemble divergence during transition.

The system must distinguish actual regime transitions from noisy feature fluctuations.

---

## 100. REGIME-CONDITIONED PERFORMANCE

ForecastGuard performance should be evaluated separately across important regimes.

The system should determine whether:

    universal model

or:

    regime-conditioned model

performs better.

Possible evaluation groups include:

- cyclone-related cases,
- heavy-rain cases,
- monsoon active cases,
- monsoon break cases,
- western disturbances,
- heat-wave-related cases,
- ordinary weather cases.

Event-specific models must not be introduced merely because they perform well on small samples.

---

## 101. HISTORICAL ANALOGUE ENGINE

ForecastGuard should maintain a historical database of previously observed forecast situations.

A basic analogue system searches for historical atmospheric states similar to the current state.

The historical record should connect:

    initial state
        |
        v
    forecast trajectory
        |
        v
    verified outcome

This creates a searchable historical forecast-memory system.

---

## 102. ATMOSPHERIC ANALOGUES

At prediction time, the system may search for historical atmospheric states that resemble the current state.

Similarity may use:

- geopotential patterns,
- pressure patterns,
- wind fields,
- moisture structure,
- temperature anomalies,
- precipitation structure,
- regime indicators.

Analogue retrieval must be evaluated against simple baselines.

---

## 103. FORECAST-TRAJECTORY ANALOGUES

ForecastGuard should go beyond matching only atmospheric initial states.

It should investigate whether the current forecast trajectory resembles historical forecast trajectories that later succeeded or failed.

Conceptually:

    CURRENT TRAJECTORY
            |
            v
    SEARCH HISTORICAL TRAJECTORIES
            |
            v
    SIMILAR PATHWAYS
            |
            v
    VERIFIED OUTCOMES

This directly tests the forecast-pathway hypothesis.

---

## 104. TRAJECTORY MEMORY

Each historical case should ideally contain:

    atmospheric state
    forecast trajectory
    ensemble evolution
    model-relative behaviour
    verified error
    failure fingerprint
    reliability trajectory

This allows ForecastGuard to search for similar reliability pathways.

---

## 105. FAILURE PATHWAY MEMORY

The system should maintain a specialized subset of historical cases containing significant forecast failures.

A failure pathway may contain:

    initial conditions
        |
        v
    forecast evolution
        |
        v
    uncertainty evolution
        |
        v
    reliability degradation
        |
        v
    verified failure

The objective is not to claim that the current case will repeat exactly.

Instead, the system should identify whether the current case resembles previously observed pathways.

---

## 106. ANALOGUE OUTPUT

The analogue engine should produce machine-readable results such as:

    analogue_id
    similarity_score
    historical_date
    forecast_cycle
    lead_time
    region
    outcome
    severity
    failure_type

The user interface may summarize these results as evidence.

Example language:

> Similar historical trajectories showed elevated failure frequency.

Exact percentages must only be displayed when actually calculated from the retrieved cases.

---

## 107. ANALOGUE CALIBRATION

Analogue similarity does not automatically imply predictive power.

The system must evaluate:

    similarity
        vs
    future error

and determine whether highly similar historical cases actually provide useful information.

The analogue engine should therefore be tested using chronological out-of-sample evaluation.

---

## 108. ORDINARY ANALOGUES VERSUS FAILURE PATHWAYS

ForecastGuard should compare:

    ordinary atmospheric analogues

against:

    forecast-trajectory analogues

and:

    failure-pathway analogues.

This determines whether specialized forecast-memory provides value beyond conventional weather analogues.

---

## 109. ANALOGUE KILL TESTS

The analogue system should be simplified or removed if:

1. analogues do not beat the baseline;
2. trajectory analogues do not beat atmospheric analogues;
3. failure pathways do not improve risk prediction;
4. performance disappears under chronological testing;
5. results depend on future information;
6. analogue similarity is not calibrated with actual outcomes.

The final product should only expose analogue evidence that has demonstrated measurable value.

---

## 110. FAILURE PATHWAY ATLAS

ForecastGuard should eventually maintain a Failure Pathway Atlas.

Each pathway may contain:

    forecast trajectory
    ensemble evolution
    model-relative evolution
    atmospheric regime
    reliability-state transitions
    first warning
    verified failure
    failure morphology
    alert history
    prediction confidence
    final verification

This atlas becomes a long-term memory of forecast reliability behaviour.

---

## 111. HISTORICAL MEMORY AS EVIDENCE

Historical analogue results should be treated as evidence, not proof.

Correct interpretation:

> Historical cases with similar forecast evolution frequently experienced degradation.

Incorrect interpretation:

> This forecast will fail because a similar historical case failed.

The system must preserve this distinction in both model logic and user-facing explanations.
# CHUNK 6 — NOVELTY, FRAGILITY, AI RISK ENGINE AND EVIDENCE

## 112. OOD / NOVELTY ANALYSIS

ForecastGuard should determine whether the current atmospheric or forecast state lies within a well-represented region of the historical reference distribution.

The purpose is not to declare an event unprecedented.

The purpose is to identify situations where historical training evidence is sparse.

The system should therefore use terminology such as:

> State lies outside the high-density region of the historical reference distribution.

rather than:

> This event has never happened before.

---

## 113. OOD REPRESENTATION

OOD analysis may operate on:

- atmospheric-state features,
- forecast-state features,
- trajectory representations,
- ensemble representations,
- or combinations of these.

Potential methods include:

- distance-based methods,
- density estimation,
- Gaussian mixture models,
- isolation methods,
- learned embeddings,
- normalizing flows,
- other validated density-estimation approaches.

A simple baseline must be established before advanced methods.

---

## 114. HISTORICAL REFERENCE DISTRIBUTION

OOD analysis requires an explicitly defined reference population.

The reference population must identify:

- time period,
- geographical domain,
- variables,
- preprocessing,
- normalization,
- model version,
- season,
- and any filtering applied.

Changing the reference population changes the interpretation of the OOD score.

---

## 115. OOD SCORE

The OOD subsystem should produce a continuous novelty or representativeness score.

Conceptually:

    OOD_score =
        degree of departure from historical reference distribution

The exact mathematical definition depends on the selected method.

The score must not automatically become a bust probability.

OOD and forecast error are different concepts.

---

## 116. OOD AS EVIDENCE QUALITY

OOD should primarily influence:

- confidence,
- evidence quality,
- model uncertainty,
- and abstention behaviour.

For example:

    familiar state
        +
    strong validated predictor
        =
    higher evidence quality

while:

    highly novel state
        +
    sparse historical evidence
        =
    reduced evidence quality

This distinction prevents novelty from being incorrectly interpreted as failure.

---

## 117. OOD VALIDATION

The OOD module must be evaluated on whether it predicts:

- poor calibration,
- elevated error,
- unusual forecast behaviour,
- or reduced model reliability.

If OOD provides no useful information beyond simpler predictors, it should be removed.

---

# 118. ENSEMBLE-BASED FRAGILITY

ForecastGuard may investigate an ensemble-based fragility proxy.

The concept is:

> How strongly do initially similar ensemble scenarios diverge into materially different downstream outcomes?

The system must not describe this as a true counterfactual sensitivity experiment.

It is an ensemble-derived fragility proxy.

---

## 119. FRAGILITY CONSTRUCTION

A possible procedure is:

    identify initially similar members
            |
            v
    follow their downstream evolution
            |
            v
    measure divergence
            |
            v
    compare against later verified error

The exact similarity and divergence definitions must be validated.

---

## 120. FRAGILITY FEATURES

Candidate features include:

- initial member similarity,
- downstream member divergence,
- divergence rate,
- branch separation,
- outcome spread,
- branch persistence,
- spatial separation,
- event disagreement.

These features should be compared with conventional ensemble spread.

---

## 121. FRAGILITY BASELINE

The minimum comparison is:

    ensemble spread

versus:

    ensemble spread + fragility proxy

The fragility module must demonstrate incremental value.

A visually impressive fragility calculation without predictive improvement must not become part of the core model.

---

## 122. FRAGILITY KILL TEST

Remove the fragility module if:

1. it does not improve validation;
2. it merely reproduces ensemble spread;
3. it is unstable across regions;
4. it depends on future information;
5. it does not improve calibration;
6. it does not improve warning lead time.

---

# 123. AI RISK ENGINE

The AI Risk Engine is responsible for estimating future forecast reliability.

Its central prediction is not simply:

    forecast = bust / not bust

Instead, the system should estimate the probability of future forecast failure given information available at the current lead time.

Conceptually:

    P(Bust | Information available now)

The system should also support severity-aware predictions.

---

## 124. MODEL LADDER

ForecastGuard must follow a controlled model-development ladder.

### Model 0 — Climatology

Estimate historical bust frequency conditioned on:

- region,
- season,
- lead time,
- and other justified conditioning variables.

### Model 1 — Statistical baseline

Possible models:

- logistic regression,
- calibrated generalized linear model,
- other simple probabilistic models.

### Model 2 — Structured machine learning

Possible models:

- XGBoost,
- LightGBM,
- other validated tree-based methods.

### Model 3 — Temporal model

Only if justified:

- temporal convolution,
- LSTM,
- temporal transformer,
- or another sequence model.

### Model 4 — Spatial representation

Only if spatial fields demonstrably add predictive value.

Complex models must not be adopted merely because they are modern.

---

## 125. BASELINE-FIRST DEVELOPMENT

Every advanced model must be compared with simpler alternatives.

Required conceptual ladder:

    climatology
        <
    spread-only
        <
    basic statistical model
        <
    structured ML
        <
    ensemble dynamics
        <
    multi-model intelligence
        <
    trajectory intelligence
        <
    regime / OOD
        <
    fragility

The exact ordering may change during experimentation.

The important principle is controlled incremental evaluation.

---

## 126. FEATURE GROUPS

The risk engine may receive feature groups including:

### Forecast state

- lead time,
- forecast magnitude,
- spatial gradients,
- forecast anomalies.

### Ensemble behaviour

- mean,
- spread,
- spread growth,
- spread acceleration,
- clustering,
- branching,
- coherence,
- multimodality.

### Forecast trajectory

- run-to-run changes,
- persistence,
- jumpiness,
- trend,
- change points.

### Multi-model

- model disagreement,
- model-relative distance,
- divergence trend,
- NCMRWF outlier behaviour.

### Atmospheric state

- geopotential,
- pressure,
- wind,
- moisture,
- CAPE,
- vorticity,
- divergence,
- shear,
- temperature.

### Historical memory

- analogue similarity,
- failure-pathway similarity,
- historical failure frequency.

### Novelty

- OOD score,
- historical density,
- representativeness.

### Fragility

- ensemble-based fragility indicators.

Not all feature groups are guaranteed to survive validation.

---

## 127. TARGET DESIGN

The primary target should support probabilistic risk prediction.

Possible target:

    bust_probability

A secondary target may represent:

    continuous normalized forecast error

A third target may represent:

    bust severity

The exact target configuration must be determined through validation.

The system should avoid forcing a continuous scientific phenomenon into an unnecessarily crude binary target.

---

## 128. HAZARD / TIME-TO-FAILURE REPRESENTATION

ForecastGuard should investigate a hazard-style formulation.

Define:

    H_t(tau) =
        probability of failure within future interval tau
        given information available at time t

This allows the system to represent not only:

    Will it fail?

but also:

    How soon might meaningful failure occur?

This is useful for operational warning lead time.

---

## 129. FAILURE TIME

Define:

    T_failure =
        time at which the forecast satisfies the verified bust criterion

Define:

    T_alert =
        first time ForecastGuard produces an actionable alert

Then:

    warning_lead_time =
        T_failure - T_alert

This quantity should become a core operational evaluation metric.

---

## 130. EARLIEST TRUSTWORTHY WARNING

The objective is not to issue the earliest possible alert at any cost.

The objective is:

> Find the earliest warning that remains sufficiently accurate and actionable.

Therefore the system should evaluate warning lead time jointly with:

- false alarms,
- calibration,
- alert stability,
- precision,
- recall,
- and operational usefulness.

---

## 131. FAILURE MORPHOLOGY PREDICTION

ForecastGuard should investigate whether the system can predict the future shape of forecast failure.

Define:

    M_future =
    {
        location,
        timing,
        intensity,
        structure,
        event_type
    }

The prediction is:

    P(M_future | information available now)

The model must not use future verification information as an input.

---

## 132. FAILURE TYPE

Potential failure types include:

- intensity error,
- spatial displacement,
- timing error,
- missed event,
- false alarm,
- structural error,
- mixed failure.

Multiple failure types may occur simultaneously.

The architecture should therefore support multi-label or structured failure representation where justified.

---

## 133. RISK FUSION

Multiple scientific signals may eventually contribute to a unified risk estimate.

Potential evidence sources:

    ensemble dynamics
    forecast trajectory
    model disagreement
    atmospheric regime
    historical memory
    OOD
    fragility

The system must not assign arbitrary manual weights simply because they appear intuitive.

Fusion weights or model relationships should be learned and validated.

---

## 134. PROBABILITY CALIBRATION

Raw machine-learning probabilities are not automatically trustworthy.

ForecastGuard must include a calibration stage.

Potential methods include:

- Platt scaling,
- isotonic regression,
- beta calibration,
- other validated probabilistic calibration methods.

Calibration must be performed without contaminating the final test set.

---

## 135. CALIBRATION EVALUATION

The system should evaluate:

- Brier score,
- reliability diagrams,
- calibration error,
- probability histograms,
- sharpness,
- discrimination.

A model with slightly lower classification accuracy but substantially better calibrated probabilities may be more useful operationally.

---

## 136. SELECTIVE PREDICTION / ABSTENTION

ForecastGuard should be allowed to express uncertainty about its own evidence.

Potential output:

    HIGH CONFIDENCE
    MODERATE CONFIDENCE
    LOW CONFIDENCE
    INSUFFICIENT EVIDENCE

This is separate from forecast bust probability.

For example:

    Bust probability = high
    Evidence quality = low

means:

> The available evidence suggests elevated risk, but historical/model support is weak.

This distinction should be preserved.

---

## 137. EVIDENCE QUALITY

Evidence quality may incorporate:

- OOD status,
- missing features,
- data quality,
- analogue availability,
- ensemble completeness,
- model availability,
- model calibration regime,
- and historical support.

Evidence quality should never simply be another name for risk probability.

---

## 138. EXPLANATION ENGINE

The Explanation Engine translates validated model evidence into human-readable reasoning.

The explanation system should answer:

> Why is ForecastGuard concerned?

Potential evidence categories:

    Ensemble divergence
    Forecast trajectory instability
    Multi-model disagreement
    Atmospheric regime transition
    Historical pathway similarity
    Low historical representation
    Ensemble-based fragility

The explanation must reference actual computed evidence.

---

## 139. EXPLANATION HIERARCHY

The user-facing explanation should follow:

    RISK
      |
      v
    CHANGE
      |
      v
    EVIDENCE
      |
      v
    DETAILS

Example structure:

    Bust risk: elevated

    Risk increased because:
      1. ensemble divergence increased
      2. successive forecasts shifted materially
      3. comparable historical trajectories degraded

Each statement must be generated from actual model outputs.

---

## 140. FEATURE ATTRIBUTION

For machine-learning models, ForecastGuard may use methods such as:

- SHAP,
- permutation importance,
- feature contribution analysis,
- partial dependence where appropriate.

Attribution must be interpreted carefully.

A feature being important to the model does not prove that it physically causes forecast failure.

User-facing wording should therefore prefer:

> Strong contributor to the model's risk estimate.

rather than:

> Cause of the forecast failure.

---

## 141. SPATIAL EXPLANATIONS

Where possible, the system should identify where the evidence is concentrated.

Potential outputs:

- high-risk regions,
- error-prone areas,
- ensemble divergence zones,
- forecast-observation mismatch regions,
- model disagreement hotspots.

Spatial explanations must be generated from actual spatial calculations.

---

## 142. EVIDENCE TRACEABILITY

Every displayed explanation should be traceable to an underlying computation.

For example:

    "Ensemble divergence increased"

must map to stored:

    ensemble_divergence_metric

and:

    relevant forecast cycle
    relevant lead time
    relevant spatial region.

This makes the system auditable.

---

## 143. EVIDENCE CONTRADICTIONS

ForecastGuard should explicitly recognize contradictory evidence.

Examples:

### False confidence

    low ensemble spread
    +
    high eventual error

### Conservative uncertainty

    high ensemble spread
    +
    low eventual error

### False consensus

    high model agreement
    +
    high eventual error

### Non-actionable ambiguity

    high model disagreement
    +
    low eventual error

These cohorts can be used for scientific analysis and model improvement.

---

## 144. NEGATIVE KNOWLEDGE

The system should catalogue signals that appear intuitive but do not reliably predict forecast failure.

Examples may include:

- isolated forecast jumps,
- high ensemble spread alone,
- isolated model disagreement,
- isolated OOD status.

The final model should learn not only:

> what predicts failure

but also:

> when conventional warning signals are insufficient.

This prevents overconfident interpretation of weak indicators.

---

## 145. AI OUTPUT CONTRACT

The AI Risk Engine should expose a structured output.

Conceptually:

    {
        risk_probability,
        risk_change,
        severity_probability,
        failure_location,
        failure_timing,
        failure_type,
        evidence_quality,
        confidence,
        top_evidence,
        model_version
    }

The exact schema will be implemented in the API layer.

No UI component should invent fields that are not produced by the backend.
# CHUNK 7 — OPERATIONAL LAYER, REPLAY, BACKEND, DATABASE AND FRONTEND

## 146. OPERATIONAL DECISION LAYER

The Operational Decision Layer converts validated ForecastGuard outputs into a form that supports human review and action.

The system should not overwhelm the primary operational interface with every available scientific feature.

Core principle:

> Simple outside. Deep inside.

The main operational interface should surface:

- current reliability,
- bust probability,
- reliability change,
- affected region,
- forecast lead time,
- major evidence,
- evidence quality,
- and actionable alerts.

Advanced scientific information should remain accessible through progressive disclosure.

---

## 147. RELIABILITY STATE

ForecastGuard may present a user-facing reliability state such as:

    STABLE
    WATCH
    DEGRADING
    HIGH RISK
    CRITICAL

These labels are interface states.

They must only be mapped to scientifically validated probability or decision thresholds after model validation.

They must not be treated as physical atmospheric states.

---

## 148. RELIABILITY SCORE

The interface may expose a reliability score representing the current assessed trustworthiness of the forecast.

The score must be derived from the backend risk/calibration system.

It must never be hardcoded.

The system should distinguish:

    forecast reliability

from:

    model evidence quality

A forecast can have moderate reliability with strong evidence, or high apparent reliability with weak evidence.

---

## 149. BUST RISK

The interface should prominently display the probability of meaningful forecast failure.

Example conceptual display:

    BUST RISK
    68%

The number must always come from the calibrated risk engine.

If the evidence is insufficient, the interface must be capable of displaying:

    Insufficient evidence

rather than a misleading numerical value.

---

## 150. RISK CHANGE

Operational users need to know not only the current risk but whether it is changing.

The system should therefore expose:

    current risk

and:

    change since previous forecast cycle

Potential representations:

    +12 percentage points

or:

    Risk increasing

The comparison baseline must be clearly defined.

---

## 151. RELIABILITY TIMELINE

The main interface should provide a D+1 through D+10 reliability trajectory where data are available.

Conceptually:

    D+1   D+2   D+3   D+4   D+5   D+6   D+7   D+8   D+9   D+10
     |     |     |     |     |     |     |     |     |     |
    ---   ---   ---   ---   ---   ---   ---   ---   ---   ---

The timeline should communicate:

- current risk,
- future risk,
- direction of change,
- alert transitions,
- and confidence/evidence quality.

---

## 152. INDIA RISK MAP

The central operational visualization should be a map-first representation.

The map should answer:

> WHERE is the forecast most vulnerable?

Potential layers include:

- reliability,
- bust probability,
- expected error,
- error-prone regions,
- ensemble divergence,
- model disagreement,
- forecast-observation difference during replay.

The map must use actual backend-generated spatial fields.

---

## 153. PROGRESSIVE DISCLOSURE

The operational screen should reveal complexity gradually.

Primary level:

    What is happening?

Secondary level:

    Where is the problem?

Tertiary level:

    Why is ForecastGuard concerned?

Advanced level:

    Show scientific evidence.

Research level:

    Show underlying features, model diagnostics and experiments.

This allows the same system to serve both operational users and researchers.

---

## 154. WHY IS RELIABILITY LOW?

The interface should provide an evidence panel explaining major drivers.

Possible evidence categories:

    Ensemble divergence
    Forecast instability
    Multi-model disagreement
    Atmospheric regime transition
    Historical pathway similarity
    Low historical representation
    Ensemble fragility

Only validated and currently available evidence should appear.

---

## 155. EVIDENCE QUALITY PANEL

The interface should display whether the current risk assessment has strong or weak evidence.

Possible factors:

- data completeness,
- ensemble completeness,
- historical analogue support,
- OOD status,
- model availability,
- calibration coverage.

The panel should make clear:

> Evidence quality is not the same thing as bust probability.

---

## 156. ALERT SYSTEM

ForecastGuard should generate alerts when risk crosses validated operational thresholds.

An alert should contain:

    alert_id
    timestamp
    forecast_run
    affected_region
    lead_time
    risk_probability
    severity
    reason
    evidence_quality
    model_version

Alerts should be persisted for later evaluation.

---

## 157. ALERT STABILITY

An operational alert system must avoid unnecessary oscillation.

The system should measure:

- alert reversals,
- alert duration,
- repeated escalation/de-escalation,
- false escalation,
- persistence above threshold.

A model that performs well statistically but produces unstable alerts may be operationally weak.

---

## 158. ALERT THRESHOLDS

Alert thresholds must be determined using validation and operational utility.

They should not be selected merely because they produce attractive dashboard behaviour.

Potential evaluation points include:

- fixed false-alarm rate,
- precision,
- recall,
- warning lead time,
- calibration,
- and alert frequency.

---

## 159. OPERATIONAL MODE

Operational Mode should prioritize:

- current forecast cycle,
- current reliability,
- active alerts,
- affected regions,
- lead-time trajectory,
- major evidence,
- and concise explanations.

It should avoid overwhelming the user with experimental scientific diagnostics.

---

## 160. INVESTIGATOR MODE

Investigator Mode should expose deeper diagnostics.

Possible modules:

- ensemble geometry,
- model comparison,
- atmospheric regime,
- historical analogues,
- OOD,
- failure pathway memory,
- feature attribution,
- reliability trajectory,
- verification diagnostics.

This mode is intended for deeper forecast investigation.

---

## 161. RESEARCH MODE

A Research Mode may expose experimental features that are not part of the operational decision layer.

Examples:

- topological analysis,
- information-theoretic features,
- experimental causal discovery,
- alternative embeddings,
- experimental fragility metrics.

Experimental outputs must be clearly marked.

They must not be presented as operationally validated signals unless they pass the validation protocol.

---

# 162. HISTORICAL REPLAY ENGINE

ForecastGuard must support historical replay.

Replay is not a fake demo.

It is a scientific backtest in which the system reconstructs what it would have known at each historical forecast lead.

Conceptually:

    HISTORICAL CASE
          |
          v
    D+1 information
          |
          v
    ForecastGuard prediction
          |
          v
    D+2 information
          |
          v
    ForecastGuard prediction
          |
          v
          ...
          |
          v
    verified outcome

---

## 163. REPLAY INFORMATION BOUNDARY

At each replay time, the system must enforce the same information boundary that existed operationally.

For example:

    D+3 replay

may use only information available at D+3.

It must not access:

    D+4 or later observations

or any future-derived predictor.

This is essential for credible backtesting.

---

## 164. REPLAY TIMELINE

The interface should allow the user to move through the historical case.

Conceptually:

    D+1 → D+2 → D+3 → D+4 → D+5 → ... → verification

At each point show:

- forecast,
- reliability estimate,
- risk,
- evidence,
- ensemble state,
- model disagreement,
- historical evidence,
- and what happened later.

---

## 165. FORECAST VERSUS REALITY

The replay interface should eventually compare:

    FORECAST

against:

    OBSERVED REALITY

Potential views:

- side-by-side maps,
- error map,
- time series,
- event track,
- spatial displacement,
- failure fingerprint.

This provides direct visual verification.

---

## 166. FORECAST AUTOPSY

After a forecast bust is verified, ForecastGuard should perform an automated or semi-automated autopsy.

The autopsy should answer:

    What failed?

    When did the forecast begin degrading?

    When did ForecastGuard first detect elevated risk?

    Which signals were active?

    Which signals were absent?

    Was the alert early enough?

    Was the alert a false alarm?

    Did the system overestimate confidence?

    Did conventional ensemble spread identify the problem?

    Did ForecastGuard provide incremental information?

---

## 167. FAILURE PATHWAY VISUALIZATION

The autopsy should visualize the complete pathway:

    INITIAL FORECAST
          |
          v
    FORECAST EVOLUTION
          |
          v
    ENSEMBLE EVOLUTION
          |
          v
    MODEL DISAGREEMENT
          |
          v
    RELIABILITY CHANGE
          |
          v
    FIRST ALERT
          |
          v
    VERIFIED FAILURE

This should help users understand not only that a bust occurred, but how the system detected its development.

---

## 168. BUST ATLAS

The Bust Atlas should store verified historical failures.

Each case may contain:

    case_id
    date
    forecast_cycle
    region
    variable
    lead_time
    severity
    failure_type
    failure_fingerprint
    risk_trajectory
    alert_history
    evidence_history
    verification_metrics

The atlas should be searchable.

---

## 169. BACKEND ARCHITECTURE

The backend should use:

    FastAPI
    Python
    Pydantic

The backend is responsible for:

- data access,
- scientific computation interfaces,
- model inference,
- risk retrieval,
- verification retrieval,
- alert management,
- replay,
- autopsy,
- and API validation.

Scientific computation should remain modular rather than embedded directly into HTTP route handlers.

---

## 170. BACKEND MODULE BOUNDARIES

Conceptual backend structure:

    backend/
        api/
        schemas/
        services/
        scientific/
        models/
        verification/
        features/
        replay/
        alerts/
        database/
        configuration/
        tests/

API routes should orchestrate services rather than contain large scientific algorithms.

---

## 171. API DESIGN

The API should expose versioned endpoints.

Potential endpoints include:

    /api/v1/forecasts
    /api/v1/reliability
    /api/v1/risk
    /api/v1/maps
    /api/v1/alerts
    /api/v1/verification
    /api/v1/analogues
    /api/v1/replay
    /api/v1/autopsy
    /api/v1/models
    /api/v1/health

The exact endpoint structure may evolve during implementation.

---

## 172. API PRINCIPLE

The API must return actual computed system state.

The frontend must not contain hidden scientific calculations that duplicate backend logic.

Correct architecture:

    scientific pipeline
          |
          v
       backend
          |
          v
         API
          |
          v
       frontend

This keeps scientific logic centralized and auditable.

---

## 173. API RESPONSE DESIGN

Responses should contain sufficient metadata to make outputs interpretable.

For example:

    forecast initialization
    valid time
    lead time
    region
    variable
    model version
    risk probability
    confidence
    evidence quality
    generated timestamp

This prevents the frontend from displaying ambiguous numbers.

---

## 174. DATABASE ARCHITECTURE

The primary relational database should use:

    PostgreSQL

Spatial data should use:

    PostGIS

The database should store metadata, relationships, verification summaries, model outputs, alerts, and spatial references.

Large multidimensional scientific fields should generally remain in scientific storage rather than being forced into relational tables.

---

## 175. SPATIAL DATABASE RESPONSIBILITIES

PostGIS may be used for:

- region definitions,
- administrative boundaries,
- forecast-risk polygons,
- alert regions,
- spatial indexing,
- geospatial queries,
- and metadata associated with spatial products.

Large raster fields should use appropriate scientific storage.

---

## 176. SCIENTIFIC STORAGE

ForecastGuard should use:

    GRIB2
        for immutable source forecast files

    Zarr
        for chunked multidimensional scientific datasets

    Parquet
        for tabular features and verification records

This separation is intended to improve:

- scalability,
- reproducibility,
- scientific workflow compatibility,
- and performance.

---

## 177. FRONTEND ARCHITECTURE

The frontend should use:

    Next.js
    React
    TypeScript
    Tailwind CSS

Scientific visualization should use appropriate specialized libraries.

Potential stack:

    MapLibre GL JS
    deck.gl
    Apache ECharts
    Motion / Framer Motion
    Lucide icons

The final frontend should prioritize clarity and operational usability.

---

## 178. MAP VISUALIZATION

MapLibre and/or deck.gl may be used for spatial visualization.

The map system should support:

- India-focused views,
- zoom,
- pan,
- layer switching,
- risk overlays,
- regional highlighting,
- forecast fields,
- error fields,
- and replay comparison.

Map rendering should consume backend-provided data.

---

## 179. CHART VISUALIZATION

Apache ECharts may be used for:

- reliability trajectories,
- risk probability,
- ensemble distributions,
- model comparison,
- time series,
- calibration curves,
- verification statistics,
- and alert histories.

Charts must clearly identify:

- variable,
- units,
- lead time,
- forecast cycle,
- and whether data are forecast, prediction, or verification.

---

## 180. UI INFORMATION HIERARCHY

The main interface should follow:

    WHERE
       |
       v
    WHEN
       |
       v
    HOW
       |
       v
    WHY
       |
       v
    EVIDENCE
       |
       v
    VERIFICATION

Specifically:

    MAP       = WHERE
    TIMELINE  = WHEN
    FINGERPRINT = HOW
    DRIVER PANEL = WHY
    HISTORICAL MEMORY = HAVE WE SEEN THIS PATHWAY?
    EVIDENCE = WHY BELIEVE THE SYSTEM?
    AUTOPSY = DID IT ACTUALLY WORK?

This hierarchy should guide the UI implementation.

---

## 181. UI DESIGN PRINCIPLE

The main dashboard should feel simple despite a scientifically deep backend.

The system should communicate:

    Simple outside.
    Deep inside.

The primary screen should avoid exposing every experimental feature simultaneously.

Advanced details should be accessible through:

- expandable panels,
- drill-down views,
- investigator mode,
- replay mode,
- and research diagnostics.

---

## 182. UI SOURCE OF TRUTH

The approved ForecastGuard dashboard design is the visual source of truth for the implementation.

The implementation should preserve its major visual language:

- dark charcoal / near-black environment,
- amber/golden ForecastGuard brand accent,
- restrained atmospheric visual effects,
- strong map-first composition,
- left navigation,
- top operational header,
- prominent reliability panel,
- bust-risk display,
- reliability trajectory,
- evidence panel,
- and supporting scientific modules.

The exact visual appearance should be refined during implementation, but the design must remain aligned with the approved concept.

---

## 183. FRONTEND DATA RULE

The frontend must never fabricate scientific values.

During development, mock data may be used only when clearly marked as development/demo data.

Production scientific views must consume actual API results.

Placeholder values must never be presented as real forecast skill or real ForecastGuard performance.

---

## 184. RESPONSIVE AND OPERATIONAL READABILITY

The interface should prioritize:

- readability,
- hierarchy,
- high information density without clutter,
- clear alert states,
- map visibility,
- accessible controls,
- and presentation-distance legibility.

Important operational values should not depend on tiny text.

---

## 185. FRONTEND STATE MANAGEMENT

The frontend should maintain a clear state model for:

- selected forecast cycle,
- selected lead time,
- selected region,
- active map layer,
- operational/investigator mode,
- replay state,
- selected alert,
- selected historical case.

State should not be duplicated unnecessarily across components.

---

## 186. FRONTEND ERROR STATES

The UI must explicitly handle:

    loading
    unavailable data
    stale data
    incomplete data
    failed API requests
    insufficient evidence
    missing ensemble members
    unavailable model comparison
    unavailable historical analogues

The interface must never silently replace missing scientific data with zero or fabricated values.
# CHUNK 8 — SCIENTIFIC PIPELINE, DATA ENGINEERING, VERIFICATION, FEATURES, ML AND EXPERIMENT GOVERNANCE

## 187. SCIENTIFIC PIPELINE PRINCIPLE

ForecastGuard's scientific pipeline must transform raw atmospheric forecast data into a verified, reproducible reliability assessment.

The complete chain should remain traceable:

    RAW FORECAST
        |
        v
    QUALITY CONTROL
        |
        v
    TEMPORAL / SPATIAL ALIGNMENT
        |
        v
    OBSERVATION MATCHING
        |
        v
    FORECAST ERROR
        |
        v
    BUST LABEL / CONTINUOUS ERROR TARGET
        |
        v
    FEATURE ENGINEERING
        |
        v
    MODEL PREDICTION
        |
        v
    CALIBRATION
        |
        v
    OPERATIONAL RISK
        |
        v
    VERIFICATION
        |
        v
    MODEL LEARNING / AUDIT

No stage should silently modify scientific meaning.

---

## 188. RAW DATA INGESTION

The ingestion layer should obtain authorized real forecast and observation data.

Primary initial forecast source:

    NCMRWF / TIGGE

Primary initial verification source:

    IMD-NCMRWF merged daily rainfall analysis

Additional datasets may be introduced only after the first pipeline is scientifically stable.

Potential future sources include:

- other TIGGE centres,
- IMDAA,
- ERA5,
- INSAT products,
- IMD temperature observations,
- cyclone best-track datasets,
- other authorized observational products.

Each source must have a dataset registry.

---

## 189. DATASET REGISTRY

Every external dataset should have metadata including:

    dataset_name
    provider
    source_url / catalogue_reference
    access_method
    temporal_resolution
    spatial_resolution
    variables
    units
    coverage
    licence
    attribution
    access_restrictions
    redistribution_restrictions
    version
    retrieval_timestamp

This registry prevents undocumented data dependencies.

---

## 190. IMMUTABLE RAW DATA

Original forecast files should be preserved as immutable source artifacts whenever licensing and storage constraints permit.

For example:

    raw/
        tigge/
            centre=dems/
                date=YYYY-MM-DD/
                    cycle=00/
                        original.grib2

The raw artifact should not be overwritten after ingestion.

If preprocessing is required, the processed product should be stored separately.

---

## 191. FILE IDENTIFICATION

Every forecast file should have a deterministic identity.

The identity should encode or reference:

    centre
    model
    initialization_time
    cycle
    variable
    level
    forecast_type
    member
    lead_time
    source_dataset_version

Where possible, checksums should be stored to detect accidental modification or duplication.

---

## 192. FORECAST METADATA

For each forecast field, retain metadata such as:

    centre
    model
    model_version
    initialization_time
    valid_time
    lead_time
    variable
    level
    forecast_type
    ensemble_member
    units
    grid_definition
    source_file
    dataset_version

Model upgrade periods must remain identifiable.

A forecast from one model version should not be silently treated as identical to a forecast from another model version.

---

## 193. GRIB2 PARSING

GRIB2 files should be parsed using scientifically established libraries.

Possible tooling includes:

- eccodes
- cfgrib
- xarray

The exact parser may depend on deployment requirements.

Parsing should extract and validate:

    edition
    centre
    subCentre
    dataType
    typeOfLevel
    shortName
    paramId
    step
    startStep
    endStep
    date
    time
    perturbation / member number
    units
    grid type
    dimensions
    latitude
    longitude
    missing values

Parser behaviour should be covered by tests using representative real GRIB files.

---

## 194. FIRST DATASET D0

The first implementation dataset should remain intentionally small.

Use:

    NCMRWF / TIGGE
    centre = dems
    variable = tp
    surface field
    ensemble forecast
    00 UTC cycle
    one historical month
    India-focused domain
    D+1 through D+10
    all actually available archived members

The purpose is not model training.

The purpose is:

    DATA REALITY CHECK

---

## 195. D0 VALIDATION CHECKLIST

Before expanding the dataset, verify:

    ✓ files can be downloaded
    ✓ files can be parsed
    ✓ initialization timestamps are correct
    ✓ forecast steps are correct
    ✓ members are correctly identified
    ✓ expected members are present
    ✓ spatial coverage is correct
    ✓ coordinates are correct
    ✓ units are correct
    ✓ accumulation semantics are understood
    ✓ duplicate fields are detected
    ✓ missing fields are detected
    ✓ observation matching is possible

Do not scale the dataset until this checklist passes.

---

## 196. FORECAST ACCUMULATION SEMANTICS

Precipitation verification requires exact handling of accumulation periods.

Forecast precipitation must not be compared against observations simply because their timestamps appear similar.

The pipeline must explicitly determine:

    initialization time
        +
    forecast step
        +
    accumulation window

and map that to the corresponding observation period.

The observation period must represent the same physical rainfall accumulation window.

---

## 197. TEMPORAL ALIGNMENT

For every forecast-observation pair, record:

    forecast_initialization
    forecast_valid_start
    forecast_valid_end
    observation_valid_start
    observation_valid_end

A pair is valid only if the physical windows are compatible.

The alignment function should be deterministic and testable.

---

## 198. TIMEZONE HANDLING

Internally, timestamps should be stored in UTC.

Local observational conventions such as IMD daily rainfall ending at 0830 IST must be explicitly represented.

The pipeline must never silently mix:

    UTC
    IST
    local observation day

A documented conversion layer should handle these cases.

---

## 199. SPATIAL ALIGNMENT

Forecast and observation grids may differ.

The verification pipeline should explicitly perform:

    grid inspection
        |
        v
    coordinate normalization
        |
        v
    regridding
        |
        v
    land-mask handling
        |
        v
    verification

The regridding method must be recorded.

---

## 200. REGRIDDING POLICY

The regridding method must depend on the variable and scientific purpose.

For precipitation, the method should preserve the intended physical interpretation as far as practical.

The system should record:

    source_grid
    target_grid
    interpolation_method
    mask
    preprocessing_version

The same method should be used consistently within an experiment unless the experiment explicitly compares methods.

---

## 201. QUALITY CONTROL

Every forecast field should pass automated QC.

Minimum checks:

    file readable
    valid dimensions
    valid coordinates
    expected time
    expected lead
    valid units
    expected variable
    missing-value fraction
    physically plausible range
    duplicate detection

QC results should be stored.

---

## 202. OBSERVATION QC

Observation products should also undergo QC.

Potential checks include:

- missing grid cells,
- invalid values,
- unexpected discontinuities,
- timestamp consistency,
- coverage,
- units,
- dataset-version consistency.

Observation QC must not accidentally remove legitimate extreme weather events.

Extreme values should be investigated, not automatically deleted.

---

## 203. VERIFICATION ENGINE

The Verification Engine is one of the most important components of ForecastGuard.

Its purpose is to transform:

    forecast + observation

into:

    objective forecast error

The verification engine must be independent from the ML model.

This prevents the model from defining its own success criteria.

---

## 204. CONTINUOUS ERROR TARGET

ForecastGuard should maintain continuous error measurements.

Possible metrics include:

    MAE
    RMSE
    bias
    spatial correlation
    anomaly correlation
    precipitation event metrics

The exact metric set depends on the forecast variable.

Continuous error provides more information than a binary bust label alone.

---

## 205. SPATIAL ERROR

For gridded forecasts, calculate spatial error fields.

Conceptually:

    E(x,y,t)
      =
    Forecast(x,y,t)
      -
    Observation(x,y,t)

The system should retain these fields where storage permits.

This supports:

- error maps,
- regional analysis,
- failure morphology,
- spatial clustering,
- and forecast autopsy.

---

## 206. TEMPORAL ERROR

Where observations provide sufficient temporal resolution, the system should also calculate temporal error evolution.

For example:

    error at D+1
    error at D+2
    error at D+3
    ...
    error at D+10

This supports analysis of:

> When does the forecast begin to degrade?

---

## 207. CLIMATOLOGY NORMALIZATION

Raw error magnitude is not equally meaningful everywhere.

Forecast difficulty depends on:

- region,
- season,
- variable,
- lead time,
- climatological variability.

ForecastGuard should therefore investigate normalized error measures.

Conceptually:

    normalized_error
        =
    forecast_error
    /
    historical_expected_error

The exact normalization must be learned or defined using the training/reference population and documented.

---

## 208. BUST LABEL

The system should not depend exclusively on one arbitrary threshold.

A bust label should incorporate multiple aspects where scientifically justified:

    magnitude
    spatial displacement
    timing
    event miss
    structural error
    climatological difficulty

The final label definition must be empirically evaluated.

---

## 209. BUST SEVERITY

Potential conceptual categories:

    NORMAL
    DEGRADED
    MAJOR
    SEVERE

These are interface/analysis categories.

Their thresholds must be determined from:

- historical error distributions,
- domain knowledge,
- operational relevance,
- and validation.

They must not be chosen merely to produce convenient class sizes.

---

## 210. FAILURE FINGERPRINT

Every verified bust should receive a failure fingerprint.

Conceptually:

    LOCATION
    TIMING
    INTENSITY
    STRUCTURE
    EVENT OUTCOME

Example conceptual representation:

    Heavy-rain event
    →
    rainfall maximum displaced west
    →
    peak intensity underestimated
    →
    timing delayed by 12 h

The actual values must come from verification.

---

## 211. EVENT-SPECIFIC METRICS

Different phenomena require different verification metrics.

For rainfall:

- continuous precipitation error,
- threshold exceedance,
- spatial displacement,
- event timing.

For temperature:

- MAE,
- RMSE,
- bias,
- anomaly error.

For cyclone-related applications:

- track error,
- intensity error,
- timing,
- landfall location/timing where appropriate.

No universal metric should be assumed to be optimal for every phenomenon.

---

## 212. VERIFICATION OUTPUT TABLE

The verification layer should eventually produce records conceptually resembling:

    forecast_id
    observation_id
    initialization_time
    valid_time
    lead_time
    region
    variable
    mae
    rmse
    bias
    spatial_error
    event_error
    bust_score
    bust_class
    failure_fingerprint
    verification_version

This becomes the objective historical foundation for the ML system.

---

# 213. FEATURE ENGINEERING

Features should represent information available at prediction time.

The feature system should distinguish:

    forecast features

from:

    verification-derived targets

Verification-derived information must never leak into predictors.

---

## 214. FEATURE FAMILY A — FORECAST STATE

Initial features may include:

- lead time,
- ensemble mean,
- ensemble spread,
- ensemble percentiles,
- spatial gradients,
- temporal forecast change,
- forecast magnitude,
- anomaly relative to climatology.

These form the baseline feature set.

---

## 215. FEATURE FAMILY B — ENSEMBLE DYNAMICS

The system should go beyond simple ensemble spread.

Potential features:

    spread growth
    spread acceleration
    member divergence
    ensemble coherence
    member clustering
    cluster persistence
    branch emergence
    multimodality
    skewness
    mean-member distance

These should be evaluated individually and collectively.

---

## 216. ENSEMBLE CLUSTERING

Ensemble members may be represented in a suitable reduced-dimensional space.

Potential workflow:

    ensemble fields
        |
        v
    dimensionality reduction
        |
        v
    clustering
        |
        v
    cluster structure
        |
        v
    trajectory features

Potential algorithms:

- k-means,
- Gaussian mixture models,
- hierarchical clustering,
- density-based clustering.

The method should be selected based on validation rather than novelty.

---

## 217. ENSEMBLE BRANCHING

A forecast ensemble may begin to separate into distinct solution families.

ForecastGuard should investigate features such as:

    number of meaningful clusters
    cluster size
    cluster separation
    branch persistence
    branch emergence time

The purpose is to test whether structural ensemble separation predicts later forecast failure better than simple spread.

---

## 218. FEATURE FAMILY C — RUN-TO-RUN EVOLUTION

Successive forecast cycles should be compared.

Potential features:

    forecast displacement
    run-to-run magnitude change
    spatial correlation change
    persistence
    jumpiness
    trend
    acceleration
    forecast-cycle disagreement

These features represent the evolution of the forecast itself.

---

## 219. TWO-DIMENSIONAL FORECAST EVOLUTION

ForecastGuard should distinguish two different temporal dimensions:

    DIMENSION 1
    forecast cycle → forecast cycle

and:

    DIMENSION 2
    ensemble member → ensemble member

The interaction between these dimensions may contain useful reliability information.

The model should explicitly test whether combining them improves prediction.

---

## 220. FEATURE FAMILY D — MULTI-MODEL INFORMATION

When multiple NWP centres are available, calculate model-relative information.

Potential features:

    pairwise model distance
    ensemble-mean distance
    spatial correlation
    distribution distance
    model rank
    NCMRWF-vs-peer distance
    change in disagreement
    graph connectivity
    graph fragmentation

The goal is to distinguish:

    broad atmospheric uncertainty

from:

    NCMRWF-specific divergence.

---

## 221. MULTI-MODEL GRAPH

Represent models as nodes.

Define edges using a validated similarity/distance measure.

Conceptually:

        ECMWF
       /     \
    NCMRWF---NCEP
       \       /
        UKMO-JMA

The graph should evolve across forecast cycles.

Potential signals:

    increasing graph fragmentation
    persistent model separation
    NCMRWF becoming an outlier
    convergence after disagreement

These are hypotheses, not assumed predictive signals.

---

## 222. FEATURE FAMILY E — ATMOSPHERIC REGIME

The system should represent large-scale atmospheric context.

Potential variables:

    500 hPa geopotential height
    MSLP
    wind
    vorticity
    divergence
    moisture
    moisture convergence
    CAPE
    vertical shear
    temperature anomalies
    SST anomalies

Where available and appropriate.

---

## 223. REGIME CLASSIFICATION

Historical atmospheric states may be grouped into regimes.

Possible categories:

    stable regime
    active convection
    transition
    rapidly evolving circulation
    organized synoptic system

These labels should ideally be learned or derived from data rather than manually assigned.

---

## 224. REGIME TRANSITION

A stable regime may be easier to forecast than a rapidly changing regime.

ForecastGuard should therefore investigate:

    current regime
    regime persistence
    regime transition probability
    rate of atmospheric-state change

The hypothesis is:

> Forecast reliability may degrade disproportionately during atmospheric regime transitions.

This must be experimentally tested.

---

# 225. FEATURE FAMILY F — HISTORICAL ANALOGUES

The analogue engine should search the historical database for similar cases.

Two types should be compared:

    atmospheric-state analogues

and:

    forecast-trajectory analogues

The latter is particularly important to ForecastGuard's core hypothesis.

---

## 226. FORECAST TRAJECTORY ANALOGUE

Instead of retrieving only:

    similar atmosphere

retrieve:

    similar forecast evolution

Conceptually:

    Historical Case A
        |
        v
    forecast trajectory
        |
        v
    verified failure

    Current Case
        |
        v
    partial trajectory
        |
        v
    similarity search

This tests whether forecast evolution contains useful memory of future failure.

---

## 227. ANALOGUE OUTPUT

Potential output:

    comparable historical cases
    similarity score
    number of cases
    subsequent failure frequency
    typical failure lead time
    typical failure morphology

A statement such as:

    "9 of 13 comparable cases subsequently failed"

may only be shown if the system actually computes it from the historical database.

---

# 228. FEATURE FAMILY G — OOD / NOVELTY

ForecastGuard should estimate whether the current atmospheric state or forecast trajectory lies within the historical reference distribution.

Potential methods:

- PCA + density estimation,
- Gaussian mixture models,
- kernel density estimation,
- autoencoder embeddings,
- normalizing flows.

The simplest validated method should be preferred.

---

## 229. OOD INTERPRETATION

OOD should be phrased as:

> State lies outside the high-density region of the historical reference distribution.

It must not be interpreted as:

> This weather has never happened before.

OOD indicates limited historical representation.

It does not automatically imply forecast failure.

---

## 230. OOD AS EVIDENCE QUALITY

OOD may influence:

    evidence quality
    confidence calibration
    abstention

rather than directly forcing:

    high bust probability

This separation is important.

A novel state may still be highly predictable.

---

# 231. FEATURE FAMILY H — ENSEMBLE-BASED FRAGILITY

ForecastGuard may investigate an ensemble-based fragility proxy.

Potential concept:

    identify initially similar ensemble members
        |
        v
    observe downstream divergence
        |
        v
    calculate divergence / sensitivity proxy
        |
        v
    test against later verified error

This is not a true counterfactual sensitivity experiment.

It is an:

> ensemble-based fragility proxy

Only retain the feature if it provides measurable incremental predictive value.

---

# 232. ADVANCED EXPERIMENTAL FEATURES

Optional research experiments may include:

    persistent homology
    topological data analysis
    mutual-information decay
    transfer entropy
    causal discovery
    convergent cross mapping

These are not automatically part of the production model.

Each must pass the same kill-or-keep protocol.

---

# 233. FEATURE VERSIONING

Every feature set should have a version.

Example:

    feature_version = v0.1

The feature registry should contain:

    feature_name
    definition
    source
    units
    temporal window
    spatial window
    availability time
    transformation
    normalization
    version

This is essential for reproducibility.

---

# 234. MODEL LADDER

ForecastGuard should follow a deliberate model ladder.

    MODEL 0
    climatology

        ↓

    MODEL 1
    statistical baseline

        ↓

    MODEL 2
    tree-based ML

        ↓

    MODEL 3
    trajectory model

        ↓

    MODEL 4
    spatial representation

Complexity should increase only when the previous stage is insufficient.

---

## 235. MODEL 0 — CLIMATOLOGY

The first baseline should estimate historical bust probability using:

    region
    season
    lead time
    variable

This establishes how much skill exists before machine learning.

---

## 236. MODEL 1 — STATISTICAL BASELINE

Potential models:

    logistic regression
    calibrated generalized linear model

Advantages:

- interpretable,
- fast,
- easy to calibrate,
- strong baseline.

This model must remain a serious benchmark.

---

## 237. MODEL 2 — TREE-BASED ML

Potential algorithms:

    XGBoost
    LightGBM

These are appropriate for structured feature tables.

They can combine:

- forecast state,
- ensemble dynamics,
- run-to-run evolution,
- model disagreement,
- regime information,
- historical analogue features.

---

## 238. MODEL 3 — TRAJECTORY MODEL

Only after structured features demonstrate value should temporal models be introduced.

Potential methods:

    TCN
    LSTM
    temporal transformer

The input may represent:

    forecast state sequence
    ensemble dynamics sequence
    run-to-run sequence
    atmospheric regime sequence

The temporal model must demonstrate incremental value over engineered trajectory features.

---

## 239. MODEL 4 — SPATIAL REPRESENTATION

If spatial structure materially improves prediction, investigate:

    CNN
    spatial transformer
    graph-based spatial representation

Spatial models should only be introduced after simpler spatial summaries are evaluated.

---

# 240. TARGET DESIGN

ForecastGuard should investigate multiple prediction targets.

### Target A — Continuous error

Predict expected future error.

### Target B — Bust probability

Predict:

    P(Bust | information available now)

### Target C — Failure severity

Predict:

    P(NORMAL)
    P(DEGRADED)
    P(MAJOR)
    P(SEVERE)

### Target D — Failure morphology

Predict components such as:

    location
    timing
    intensity
    structure
    event outcome

### Target E — Failure hazard

Estimate:

    H_t(τ)
    =
    probability of failure within future interval τ

This supports warning lead-time analysis.

---

# 241. FAILURE HAZARD

The hazard formulation allows ForecastGuard to answer:

> How likely is a meaningful forecast failure to occur within the next τ hours/days?

This is more operationally useful than a single static end-of-range probability.

Potential output:

    24h failure risk
    48h failure risk
    72h failure risk

The exact horizons should follow available forecast/verification data.

---

# 242. WARNING LEAD TIME

Define:

    T_failure
        =
    time at which the forecast meets the verified failure criterion

    T_alert
        =
    first time ForecastGuard crosses the validated alert criterion

Then:

    Warning Lead Time
        =
    T_failure - T_alert

This should become one of the primary operational metrics.

---

# 243. EARLIEST TRUSTWORTHY WARNING

ForecastGuard should not maximize warning lead time at any cost.

The goal is:

> earliest warning that remains sufficiently calibrated and operationally useful.

A warning issued extremely early but frequently wrong is not necessarily useful.

---

# 244. FALSE CONFIDENCE

ForecastGuard should explicitly investigate:

    LOW ENSEMBLE SPREAD
        +
    HIGH EVENTUAL ERROR

This represents a potentially dangerous failure of conventional confidence signals.

The system should test whether it can identify these cases better than spread-only methods.

---

# 245. FALSE CONSENSUS

Another special cohort is:

    HIGH MODEL AGREEMENT
        +
    HIGH EVENTUAL ERROR

This tests whether agreement among models can create false confidence.

ForecastGuard should attempt to detect this condition where sufficient multi-model data exist.

---

# 246. RELIABILITY CONTRADICTIONS

The system should catalogue contradictory situations.

Examples:

    low spread + bad outcome
        =
    false confidence

    high spread + good outcome
        =
    conservative uncertainty

    high model agreement + bad outcome
        =
    false consensus

    high model disagreement + good outcome
        =
    non-actionable ambiguity

These cohorts may reveal weaknesses that aggregate metrics hide.

---

# 247. EVIDENCE-AWARE PREDICTION

ForecastGuard should separate:

    RISK

from:

    EVIDENCE QUALITY

The model should be capable of returning:

    high risk + strong evidence

    high risk + weak evidence

    low risk + strong evidence

    insufficient evidence

This enables more honest operational communication.

---

# 248. ABSTENTION

Where historical coverage or model evidence is insufficient, ForecastGuard may abstain.

Example:

    RELIABILITY ASSESSMENT
    Insufficient evidence

This is preferable to manufacturing a confident probability.

Selective prediction should be evaluated experimentally.

---

# 249. CALIBRATION

Raw ML probabilities should not automatically be treated as reliable probabilities.

ForecastGuard should evaluate calibration using methods such as:

    Platt scaling
    isotonic regression
    beta calibration

The final method should be selected using validation data.

Calibration must be evaluated on data not used to fit the calibration transform.

---

# 250. CALIBRATION METRICS

Primary calibration-related metrics may include:

    Brier score
    reliability diagrams
    expected calibration error
    calibration slope/intercept

Calibration should be examined across:

- lead time,
- region,
- season,
- event type,
- risk level.

---

# 251. VALIDATION SPLIT

The system should maintain separate populations:

    TRAIN
    VALIDATION
    TEST

The test set must remain untouched until model selection and tuning are complete.

---

# 252. CHRONOLOGICAL VALIDATION

Random splitting should not be the primary evaluation strategy.

Preferred structure:

    EARLIER PERIOD
        =
    TRAIN

    LATER PERIOD
        =
    VALIDATION

    UNSEEN LATER PERIOD
        =
    TEST

This better reflects operational forecasting.

---

# 253. WALK-FORWARD EVALUATION

Where feasible, ForecastGuard should use rolling/walk-forward evaluation.

Conceptually:

    Train: Year 1
    Test: Year 2

    Train: Year 1–2
    Test: Year 3

    Train: Year 1–3
    Test: Year 4

This can reveal performance stability across changing weather regimes and model eras.

---

# 254. MODEL-VERSION GENERALIZATION

NCMRWF model upgrades may change forecast-error characteristics.

Therefore experiments should investigate:

    train on earlier model era
        |
        v
    test on later model era

and, where appropriate:

    include model-version metadata

This helps determine whether ForecastGuard learns general reliability behaviour or simply memorizes one model configuration.

---

# 255. REGIONAL VALIDATION

Performance should be evaluated across relevant regions.

Possible groupings:

- northern India,
- western India,
- central India,
- eastern India,
- northeastern India,
- southern India,
- coastal regions,
- mountainous regions.

Exact regional definitions should be documented and data-driven where possible.

---

# 256. SEASONAL VALIDATION

Evaluate separately across relevant seasons.

At minimum investigate:

    winter
    pre-monsoon
    monsoon
    post-monsoon

The precise dates should be documented.

---

# 257. EVENT-BASED VALIDATION

Where sample size permits, evaluate:

    heavy rainfall
    cyclone-related situations
    monsoon transitions
    western disturbances
    heat events

Small-sample results must include uncertainty estimates.

---

# 258. PRIMARY PERFORMANCE METRICS

ForecastGuard should report:

    PR-AUC
    ROC-AUC
    Brier score
    calibration
    recall at fixed alert rate
    false-alarm rate
    warning lead time

No single metric should define success.

---

# 259. WARNING-ORIENTED EVALUATION

The central operational metric should be:

> How early can ForecastGuard detect a genuine forecast failure while maintaining an acceptable false-alarm rate?

Evaluate warning performance at fixed operating points.

For example:

    5% false-alarm rate
    10% false-alarm rate
    20% false-alarm rate

The exact operating points may change based on sample size and operational requirements.

---

# 260. ABLATION STUDY

ForecastGuard should explicitly measure the contribution of feature families.

Example:

    climatology
    +
    spread

    +
    ensemble dynamics

    +
    run-to-run evolution

    +
    multi-model

    +
    historical trajectories

    +
    regime/OOD

    +
    fragility

Each addition must demonstrate incremental value.

---

# 261. CORE COMPARISON LADDER

The final scientific comparison should resemble:

    CLIMATOLOGY
        <
    SPREAD-ONLY
        <
    BASIC ML
        <
    + ENSEMBLE DYNAMICS
        <
    + RUN-TO-RUN TRAJECTORY
        <
    + MULTI-MODEL
        <
    + HISTORICAL TRAJECTORIES
        <
    + REGIME / OOD
        <
    + FRAGILITY

Only modules that improve validated performance should survive.

---

# 262. KILL-OR-KEEP EXPERIMENTS

Every advanced feature must have a predefined failure condition.

Examples:

### Historical trajectory

If trajectory information does not beat current-state and persistence baselines:

    KILL TRAJECTORY MODULE

### Ensemble geometry

If clustering/branching does not beat spread:

    KILL ENSEMBLE-GEOMETRY MODULE

### Multi-model graph

If graph dynamics do not beat simpler model disagreement:

    KILL GRAPH MODULE

### OOD

If OOD does not improve calibration/evidence handling:

    KILL OOD MODULE

### Fragility

If ensemble fragility does not correlate with future error:

    KILL FRAGILITY MODULE

### Advanced information methods

If they do not improve operational metrics:

    KILL EXPERIMENT

---

# 263. COMPLEXITY BUDGET

ForecastGuard should maintain a practical complexity budget.

Every additional component introduces:

- computation,
- maintenance,
- interpretability cost,
- failure modes,
- data dependencies.

Therefore:

> Complexity must earn its place.

A simple calibrated model that performs better than a sophisticated architecture should be preferred.

---

# 264. EXPERIMENT TRACKING

Every major experiment should record:

    experiment_id
    dataset_version
    feature_version
    code_version
    model_type
    hyperparameters
    training_period
    validation_period
    test_period
    random_seed
    calibration_method
    metrics
    artifacts
    notes
    decision

MLflow may be used for experiment tracking.

---

# 265. MODEL REGISTRY

Production-capable models should have explicit registry entries.

Example:

    model_id
    model_version
    feature_version
    training_data_version
    calibration_version
    training_period
    validation_metrics
    test_metrics
    status

Possible statuses:

    EXPERIMENTAL
    VALIDATED
    CANDIDATE
    PRODUCTION
    RETIRED

---

# 266. MODEL PROMOTION

A model should only move toward production after:

    scientific validation
    calibration validation
    leakage audit
    reproducibility check
    integration test
    performance comparison
    human review

No model should become the production model merely because it has the highest training score.

---

# 267. DATA DRIFT

Operational monitoring should investigate changes in:

    feature distributions
    ensemble spread
    forecast error distribution
    regional behaviour
    seasonal behaviour
    OOD frequency

A model can degrade even when the software continues to run correctly.

---

# 268. CALIBRATION DRIFT

The system should monitor whether predicted probabilities remain calibrated over time.

For example:

    predicted 70% risk
        should historically correspond
    to approximately 70% event frequency

within reasonable uncertainty and sample-size limits.

Persistent calibration drift should trigger model review.

---

# 269. OOD MONITORING

Track:

    frequency of OOD states
    regions affected
    seasons affected
    model versions affected
    relationship with forecast error

This can reveal whether the reference dataset remains representative.

---

# 270. MODEL PERFORMANCE MONITORING

After deployment or operational replay, track:

    accuracy
    calibration
    warning lead time
    false alarms
    missed failures
    alert stability
    regional performance
    seasonal performance

Operational monitoring should never silently alter model parameters.

Model retraining must be an explicit governed process.

---

# 271. REPRODUCIBILITY

A scientific result should be reproducible from:

    source data version
        +
    preprocessing version
        +
    feature version
        +
    model version
        +
    configuration
        +
    code version

The system should preserve these references for every published experiment and major dashboard result.

---

# 272. DATA / CODE VERSIONING

Git should track source code.

Large datasets should be versioned or referenced using stable identifiers.

Generated scientific products should retain provenance.

Example:

    raw dataset
        →
    preprocessing v1.2
        →
    feature set v0.8
        →
    model v0.5
        →
    calibration v0.3

---

# 273. SCIENTIFIC PROVENANCE

Every risk estimate should ideally be traceable to:

    forecast source
    forecast cycle
    observation/reference source
    preprocessing version
    feature version
    model version
    calibration version

This allows an investigator to answer:

> Why did ForecastGuard produce this risk estimate?

---

# 274. EXPERIMENT ARTIFACTS

Important experiment outputs should be persisted.

Examples:

    model artifact
    metrics JSON
    calibration curves
    feature importance
    confusion matrices
    warning lead-time distribution
    regional metrics
    seasonal metrics
    test predictions
    configuration
    logs

This creates an auditable scientific record.

---

# 275. UNIT TESTING

Scientific utilities should have deterministic unit tests.

Examples:

    timestamp conversion
    accumulation-window alignment
    regridding metadata
    error calculations
    bust classification
    calibration
    alert thresholding
    warning lead time

Known analytical examples should be included where possible.

---

# 276. SYNTHETIC TEST DATA

Synthetic datasets may be used to test software behaviour.

Examples:

    known forecast field
    known observation field
    known error
    known ensemble spread
    known cluster structure
    known alert sequence

Synthetic data are appropriate for software validation.

They are not evidence of real forecast skill.

---

# 277. REAL-DATA TESTING

After software tests pass:

    synthetic data
        |
        v
    small real dataset
        |
        v
    historical experiment
        |
        v
    unseen test set

A scientific module should not be considered validated until it survives real-data testing.

---

# 278. SCIENTIFIC LEAKAGE AUDIT

Before every major experiment, explicitly inspect for leakage.

Ask:

    Was any future observation used?

    Was any future forecast cycle used?

    Was the final verification period used during tuning?

    Were labels derived using information unavailable at prediction time?

    Did preprocessing use the complete dataset?

    Did normalization use future data?

    Did analogue search accidentally include future cases?

    Did calibration use test predictions?

Every answer must be documented.

---

# 279. ANALOGUE LEAKAGE CONTROL

Historical analogue search must respect the information boundary.

If predicting a historical case at D+3:

    candidate analogue
        must be based on information available
        at the corresponding historical stage.

The analogue's future outcome may be used only as the historical target/outcome, never as part of the similarity features.

---

# 280. NORMALIZATION LEAKAGE CONTROL

Normalization statistics such as:

    mean
    standard deviation
    quantiles
    climatology

must be fitted using the appropriate training/reference population.

Future test information must not influence predictor normalization.

---

# 281. CALIBRATION LEAKAGE CONTROL

Calibration must be fitted using validation data or a dedicated calibration population.

The final test set should only be used for evaluation.

---

# 282. BLIND TEST SET

The final unseen test period should be locked before final model selection.

After model and threshold selection:

    freeze model
    freeze features
    freeze calibration
    freeze thresholds
    run blind test

This produces defensible final performance numbers.

---

# 283. SCIENTIFIC RESULT TABLE

The final system should maintain a table similar to:

    Model
    Features
    PR-AUC
    ROC-AUC
    Brier
    Calibration
    Recall @ FAR
    Warning Lead
    Regional Stability
    Seasonal Stability

Only measured results should appear.

No placeholder accuracy should be shown as scientific performance.

---

# 284. FAILURE ANALYSIS

Aggregate metrics are not sufficient.

For false positives:

    Why did ForecastGuard expect failure?

For false negatives:

    What evidence was missed?

For late warnings:

    When did useful information become available?

For unstable alerts:

    What caused the oscillation?

For false confidence:

    Why did conventional indicators remain optimistic?

This analysis should drive model improvement.

---

# 285. NEGATIVE KNOWLEDGE

ForecastGuard should explicitly preserve information about signals that failed.

Examples:

    signal appeared predictive but was not
    signal only worked in one season
    signal only worked for one event type
    signal improved training but not unseen testing
    signal improved AUC but not warning lead time

This prevents repeatedly rediscovering failed ideas.

---

# 286. FINAL SCIENTIFIC DECISION LOOP

The development loop should be:

    HYPOTHESIS
        |
        v
    FEATURE / MODEL
        |
        v
    BASELINE
        |
        v
    LEAKAGE AUDIT
        |
        v
    EXPERIMENT
        |
        v
    VALIDATION
        |
        v
    CALIBRATION
        |
        v
    OPERATIONAL METRICS
        |
        v
    KEEP / KILL
        |
        v
    DOCUMENT

This process should govern every major ForecastGuard capability.

---

# 287. SCIENTIFIC SUCCESS CRITERION

ForecastGuard should not be judged by how many AI techniques it contains.

The scientific success criterion is:

> ForecastGuard detects meaningful forecast reliability degradation earlier and/or more reliably than defensible baseline methods, while remaining calibrated, explainable, and operationally usable.

---

# 288. OPERATIONAL SUCCESS CRITERION

The operational success criterion is:

> A forecast user can quickly identify where reliability is degrading, when the risk is increasing, why the system is concerned, how strong the evidence is, and whether the warning eventually proved correct.

---

# 289. DEMONSTRATION SUCCESS CRITERION

For the SIH demonstration, the system should be able to show a complete real-data chain:

    REAL HISTORICAL FORECAST
        |
        v
    FORECAST EVOLUTION
        |
        v
    FORECASTGUARD RISK
        |
        v
    EARLY WARNING
        |
        v
    OBSERVED OUTCOME
        |
        v
    VERIFICATION
        |
        v
    AUTOPSY

The demo should make the scientific logic visible rather than merely showing a polished dashboard.

---

# 290. FINAL BUILD PRIORITY

The implementation order should remain:

    1. DATA ACCESS
    2. DATA QC
    3. FORECAST-OBSERVATION ALIGNMENT
    4. VERIFICATION ENGINE
    5. BUST DEFINITION
    6. BASELINE MODELS
    7. ENSEMBLE FEATURES
    8. RUN-TO-RUN FEATURES
    9. HISTORICAL TRAJECTORIES
    10. MULTI-MODEL
    11. REGIME / OOD
    12. FRAGILITY
    13. CALIBRATION
    14. API
    15. DASHBOARD
    16. REPLAY
    17. AUTOPSY
    18. BLIND EVALUATION

Do not reverse this order merely because the dashboard is more visually exciting.

---

# 291. GOLDEN RULE

ForecastGuard must always prefer:

    REAL DATA
        over
    MOCK DATA

    VERIFIED ERROR
        over
    ASSUMED ERROR

    BASELINE
        over
    UNJUSTIFIED COMPLEXITY

    CALIBRATED PROBABILITY
        over
    RAW MODEL SCORE

    EARLY TRUSTWORTHY WARNING
        over
    EARLY NOISY WARNING

    EVIDENCE
        over
    MARKETING

    "INSUFFICIENT EVIDENCE"
        over
    FABRICATED CERTAINTY

---

# 292. FINAL SCIENTIFIC PRINCIPLE

ForecastGuard is intended to answer a difficult operational question:

> Not simply "What does the forecast predict?"

but:

> "How much should we trust this forecast right now, how is that trust changing, what evidence indicates deterioration, and how early can we detect a meaningful failure?"

Everything in the scientific pipeline should serve that question.
# CHUNK 9 — REPOSITORY STRUCTURE, IMPLEMENTATION ROADMAP, AGENT WORKFLOW AND ENGINEERING CONTRACT

## 293. REPOSITORY PRINCIPLE

ForecastGuard should be developed as a real software/scientific system rather than as a collection of disconnected scripts.

The repository should make the separation between:

    DATA
    SCIENCE
    ML
    API
    FRONTEND
    INFRASTRUCTURE
    TESTING
    DOCUMENTATION

immediately obvious.

The repository should remain understandable to a human developer even when AI coding agents are used extensively.

---

## 294. SOURCE-OF-TRUTH

The primary source of truth should be:

    Git repository

All production code, configuration, schemas, documentation, tests, and infrastructure definitions should be version controlled.

Large raw datasets should generally not be committed directly to Git.

---

## 295. PROPOSED TOP-LEVEL STRUCTURE

The initial repository should conceptually follow:

    forecastguard/
    │
    ├── backend/
    ├── frontend/
    ├── scientific/
    ├── data/
    ├── configs/
    ├── scripts/
    ├── tests/
    ├── docs/
    ├── infra/
    ├── notebooks/
    ├── experiments/
    ├── .github/
    ├── .env.example
    ├── docker-compose.yml
    ├── Makefile
    ├── README.md
    └── LICENSE

The exact structure may evolve as implementation reveals better boundaries.

---

# 296. BACKEND DIRECTORY

Conceptually:

    backend/
    │
    ├── app/
    │   ├── main.py
    │   ├── api/
    │   ├── schemas/
    │   ├── services/
    │   ├── models/
    │   ├── database/
    │   ├── configuration/
    │   └── dependencies/
    │
    └── tests/

The backend should contain application orchestration and API-facing logic.

It should not become the dumping ground for scientific notebooks or one-off research scripts.

---

# 297. API ROUTES

Conceptually:

    backend/app/api/
        forecasts.py
        reliability.py
        risk.py
        maps.py
        alerts.py
        verification.py
        analogues.py
        replay.py
        autopsy.py
        models.py
        health.py

Routes should remain thin.

A route should generally:

    validate request
        |
        v
    call service
        |
        v
    validate response
        |
        v
    return API response

Scientific algorithms should not be buried inside route functions.

---

# 298. PYDANTIC SCHEMAS

Conceptually:

    backend/app/schemas/
        forecast.py
        reliability.py
        risk.py
        map.py
        alert.py
        verification.py
        analogue.py
        replay.py
        autopsy.py
        model.py
        common.py

Every public API response should have an explicit schema.

This reduces frontend/backend ambiguity.

---

# 299. SERVICE LAYER

Conceptually:

    backend/app/services/
        forecast_service.py
        reliability_service.py
        risk_service.py
        map_service.py
        alert_service.py
        verification_service.py
        analogue_service.py
        replay_service.py
        autopsy_service.py

Services coordinate scientific outputs and database/storage access.

They should not duplicate the scientific pipeline.

---

# 300. DATABASE LAYER

Conceptually:

    backend/app/database/
        connection.py
        models/
        repositories/
        migrations/

Database models should represent application metadata and persistent state.

Scientific multidimensional arrays should remain in appropriate scientific storage.

---

# 301. SCIENTIFIC DIRECTORY

The scientific pipeline should remain independently executable.

Conceptually:

    scientific/
    │
    ├── ingestion/
    ├── parsing/
    ├── qc/
    ├── alignment/
    ├── regridding/
    ├── verification/
    ├── climatology/
    ├── features/
    ├── ensemble/
    ├── multimodel/
    ├── regimes/
    ├── analogues/
    ├── ood/
    ├── fragility/
    ├── targets/
    ├── calibration/
    └── evaluation/

The scientific code should be usable without running the frontend.

---

# 302. DATA INGESTION

Conceptually:

    scientific/ingestion/
        tigge/
        observations/
        registry/
        manifests/

Responsibilities:

- authorized downloading,
- source identification,
- file manifests,
- metadata extraction,
- ingestion logging.

Authentication credentials must never be committed.

---

# 303. PARSING

Conceptually:

    scientific/parsing/
        grib/
        netcdf/
        metadata/

Responsibilities:

- GRIB2 parsing,
- metadata extraction,
- format normalization,
- parser validation.

---

# 304. QUALITY CONTROL

Conceptually:

    scientific/qc/
        forecast_qc.py
        observation_qc.py
        spatial_qc.py
        temporal_qc.py
        reports.py

QC should produce explicit pass/fail/warning results.

It should never silently discard data.

---

# 305. ALIGNMENT

Conceptually:

    scientific/alignment/
        temporal.py
        spatial.py
        accumulation.py
        masks.py

This module is scientifically critical.

It should contain deterministic functions for:

    forecast window
    observation window
    timezone conversion
    grid alignment
    land masking

---

# 306. VERIFICATION

Conceptually:

    scientific/verification/
        continuous.py
        spatial.py
        events.py
        severity.py
        fingerprints.py
        reports.py

This module should produce the objective forecast-error products used throughout the project.

---

# 307. TARGET GENERATION

Conceptually:

    scientific/targets/
        bust.py
        severity.py
        hazard.py
        morphology.py

Target definitions should be versioned.

Changing a bust definition must create a new target version rather than silently modifying historical labels.

---

# 308. FEATURE STORE / FEATURE PIPELINE

Conceptually:

    scientific/features/
        base.py
        ensemble.py
        run_to_run.py
        multimodel.py
        regime.py
        analogue.py
        ood.py
        fragility.py
        registry.py
        validation.py

Each feature should have a documented definition.

---

# 309. FEATURE AVAILABILITY

Every feature should explicitly record when it becomes available.

Conceptually:

    feature:
        source_time
        computation_time
        forecast_lead
        availability_boundary

This is important for leakage prevention.

A feature that requires information from D+6 cannot be used to generate a D+3 prediction.

---

# 310. ML DIRECTORY

Conceptually:

    scientific/ml/
        baselines/
        tree_models/
        temporal_models/
        spatial_models/
        calibration/
        inference/
        registry/
        evaluation/

This structure allows model complexity to evolve without rewriting the entire system.

---

# 311. BASELINE MODELS

Conceptually:

    scientific/ml/baselines/
        climatology.py
        logistic.py
        spread_only.py
        persistence.py

These baselines must remain available even after advanced models are developed.

They are essential for determining whether complexity adds value.

---

# 312. TREE MODELS

Conceptually:

    scientific/ml/tree_models/
        xgboost_model.py
        lightgbm_model.py
        training.py
        inference.py

The actual chosen implementation should depend on experiments.

Do not introduce both into production merely because both are available.

---

# 313. TEMPORAL MODELS

Conceptually:

    scientific/ml/temporal_models/
        dataset.py
        tcn.py
        lstm.py
        transformer.py
        training.py
        inference.py

These remain experimental until they demonstrate incremental value.

---

# 314. SPATIAL MODELS

Conceptually:

    scientific/ml/spatial_models/
        datasets.py
        cnn.py
        spatial_transformer.py
        training.py
        inference.py

Again:

> Spatial deep learning is earned through validation.

---

# 315. CALIBRATION MODULE

Conceptually:

    scientific/ml/calibration/
        platt.py
        isotonic.py
        beta.py
        evaluation.py

The calibration system should support experimentation and comparison.

---

# 316. EVALUATION MODULE

Conceptually:

    scientific/evaluation/
        classification.py
        calibration.py
        warning.py
        regional.py
        seasonal.py
        event.py
        ablation.py
        stability.py
        reports.py

This should become the authoritative location for scientific performance evaluation.

---

# 317. EXPERIMENTS DIRECTORY

Conceptually:

    experiments/
        001_data_validation/
        002_verification/
        003_baseline/
        004_ensemble/
        005_run_to_run/
        006_trajectory/
        007_multimodel/
        008_regime/
        009_ood/
        010_fragility/
        ...

Every experiment should have:

    hypothesis
    data version
    feature version
    model configuration
    evaluation protocol
    result
    keep/kill decision

---

# 318. EXPERIMENT NAMING

Experiment names should communicate purpose.

Prefer:

    005_run_to_run_persistence_vs_jumpiness

over:

    test2

This makes the research history understandable months later.

---

# 319. NOTEBOOK POLICY

Notebooks may be used for:

- exploration,
- visualization,
- hypothesis generation,
- debugging,
- scientific inspection.

However:

> Production logic must not live only inside notebooks.

Validated logic should be moved into tested Python modules.

---

# 320. SCRIPTS DIRECTORY

Conceptually:

    scripts/
        download/
        preprocess/
        verify/
        features/
        train/
        evaluate/
        replay/
        maintenance/

Scripts should call reusable library code.

Avoid copying scientific logic into multiple scripts.

---

# 321. CONFIGURATION

Conceptually:

    configs/
        datasets/
        regions/
        features/
        models/
        experiments/
        operational/

Configuration should be externalized wherever practical.

Avoid hardcoding:

- dataset paths,
- API endpoints,
- thresholds,
- region definitions,
- model parameters,
- credentials.

---

# 322. ENVIRONMENT VARIABLES

Sensitive or environment-specific values should be provided through environment variables.

Example conceptual variables:

    DATABASE_URL
    ECDS_API_URL
    ECDS_API_KEY
    STORAGE_ROOT

Secrets must not appear in:

    Git
    notebooks
    source code
    screenshots
    public documentation

---

# 323. .ENV.EXAMPLE

The repository should include:

    .env.example

containing variable names and safe placeholder descriptions.

It must never contain real credentials.

---

# 324. FRONTEND DIRECTORY

Conceptually:

    frontend/
    │
    ├── app/
    ├── components/
    ├── features/
    ├── lib/
    ├── hooks/
    ├── types/
    ├── styles/
    └── tests/

The frontend should consume documented APIs.

---

# 325. FRONTEND FEATURE BOUNDARIES

Potential feature groups:

    features/
        dashboard/
        map/
        reliability/
        alerts/
        ensemble/
        multimodel/
        analogues/
        replay/
        autopsy/
        verification/
        settings/

Each feature should own its UI-specific logic.

---

# 326. SHARED FRONTEND TYPES

API response types should be generated or synchronized from backend schemas where practical.

The frontend should not manually redefine scientific response structures in multiple places.

This reduces schema drift.

---

# 327. FRONTEND SCIENTIFIC RESPONSIBILITY

The frontend may perform:

- display transformations,
- formatting,
- interaction,
- filtering,
- view state.

It should not perform core scientific calculations such as:

- bust probability,
- verification,
- calibration,
- ensemble diagnostics,
- model inference.

Those belong to backend/scientific services.

---

# 328. INFRASTRUCTURE DIRECTORY

Conceptually:

    infra/
        docker/
        database/
        nginx/
        monitoring/
        deployment/

The infrastructure should eventually support local development and deployment.

---

# 329. DOCKER SERVICES

A practical initial architecture may include:

    frontend
    backend
    postgres
    scientific-worker

Optional later services:

    object storage
    cache
    monitoring
    experiment tracker

Do not introduce distributed infrastructure before the workload requires it.

---

# 330. LOCAL DEVELOPMENT

The target developer experience should eventually be:

    clone repository
        |
        v
    configure .env
        |
        v
    docker compose up
        |
        v
    backend + frontend + database
        |
        v
    run scientific pipeline commands

The system should provide clear setup documentation.

---

# 331. MAKEFILE / TASK RUNNER

Provide simple commands for common operations.

Conceptually:

    make setup
    make test
    make lint
    make format
    make backend
    make frontend
    make pipeline
    make verify
    make train
    make evaluate

Exact commands can evolve.

The goal is to make repetitive operations predictable.

---

# 332. CI/CD

GitHub Actions or equivalent CI should eventually run:

    lint
    type checking
    unit tests
    integration tests
    frontend build
    backend build
    security checks where practical

Scientific model training should not necessarily run on every commit.

---

# 333. TEST STRUCTURE

Conceptually:

    tests/
        unit/
        integration/
        scientific/
        api/
        frontend/
        end_to_end/
        leakage/

Tests should be categorized so developers can run focused subsets.

---

# 334. SCIENTIFIC TESTS

Scientific tests should verify:

    time alignment
    accumulation semantics
    regridding
    metric calculations
    bust labels
    calibration
    warning lead time
    feature availability
    leakage boundaries

Known expected analytical outcomes should be included.

---

# 335. LEAKAGE TESTS

Leakage testing should be treated as a first-class test category.

Potential automated checks:

    feature timestamp <= prediction cutoff

    training period < validation period < test period

    test labels never enter training features

    calibration data != final test data

    analogue similarity uses only allowed information

This can prevent subtle scientific errors.

---

# 336. API TESTS

API tests should cover:

    valid requests
    invalid requests
    missing data
    unavailable scientific outputs
    stale data
    schema validation
    authentication/authorization where applicable
    error responses

The API must fail explicitly rather than returning misleading values.

---

# 337. END-TO-END TEST

A complete end-to-end synthetic test should eventually exercise:

    forecast input
        |
        v
    QC
        |
        v
    alignment
        |
        v
    verification
        |
        v
    feature generation
        |
        v
    model inference
        |
        v
    risk
        |
        v
    API
        |
        v
    frontend

This confirms that the system works as one pipeline.

---

# 338. DATA CONTRACTS

Every pipeline stage should have a defined input/output contract.

Example:

    GRIB parser
        INPUT = raw GRIB2
        OUTPUT = validated forecast field + metadata

    alignment
        INPUT = forecast + observation
        OUTPUT = physically matched pair

    verification
        INPUT = matched pair
        OUTPUT = error products

    feature engine
        INPUT = prediction-time information
        OUTPUT = feature vector

    model
        INPUT = feature vector
        OUTPUT = calibrated risk

This reduces hidden dependencies.

---

# 339. SCIENTIFIC ARTIFACT CONTRACT

A scientific artifact should identify:

    artifact_type
    artifact_version
    source_dataset
    source_version
    creation_time
    code_version
    configuration
    provenance

This applies to:

- processed fields,
- feature datasets,
- models,
- predictions,
- evaluation reports.

---

# 340. DATA MANIFESTS

Each processed dataset should have a manifest.

The manifest should identify:

    files
    date range
    forecast cycles
    variables
    members
    spatial domain
    preprocessing version
    QC status

This allows incomplete datasets to be detected.

---

# 341. PIPELINE IDEMPOTENCY

Where practical, ingestion and processing jobs should be idempotent.

Running the same job twice should not create duplicate scientific records.

Use stable identities for:

    forecast run
    field
    observation
    verification pair
    feature artifact

---

# 342. JOB STATUS

Long-running scientific jobs should expose statuses such as:

    QUEUED
    RUNNING
    COMPLETE
    FAILED
    PARTIAL

Failure information should be retained.

---

# 343. PARTIAL DATA

The system must distinguish:

    zero

from:

    missing

from:

    not requested

from:

    not yet available

from:

    processing failure

This distinction is critical for both scientific interpretation and UI behaviour.

---

# 344. LOGGING

Logs should contain enough context to diagnose failures.

Important fields:

    timestamp
    job_id
    dataset
    forecast_cycle
    stage
    status
    error
    duration

Avoid logging credentials or sensitive information.

---

# 345. OBSERVABILITY

Operational monitoring should cover:

    ingestion
    processing
    API
    database
    storage
    frontend
    scientific jobs

Scientific monitoring should additionally cover:

    calibration drift
    feature drift
    OOD frequency
    forecast-error drift
    alert stability

---

# 346. AGENTIC DEVELOPMENT MODEL

AI coding agents may be used extensively, but the project must remain human-governed.

The preferred workflow is:

    HUMAN DEFINES TASK
        |
        v
    AGENT IMPLEMENTS
        |
        v
    TESTS
        |
        v
    SECOND AGENT / REVIEW
        |
        v
    HUMAN REVIEW
        |
        v
    COMMIT

No agent should silently redefine scientific methodology.

---

# 347. AGENT SPECIALIZATION

If multiple agents are used, responsibilities may be separated.

Example:

    FG-DATA
        ingestion / parsing / QC

    FG-VERIFY
        alignment / verification / labels

    FG-ML
        features / models / calibration

    FG-API
        FastAPI / database / schemas

    FG-UI
        React / maps / dashboard

    FG-QA
        testing / integration

    FG-SCIENCE-AUDITOR
        scientific review / leakage / methodology

---

# 348. FILE OWNERSHIP

Agents should have clear ownership boundaries.

Example:

    FG-DATA
        scientific/ingestion/
        scientific/parsing/
        scientific/qc/

    FG-VERIFY
        scientific/alignment/
        scientific/verification/
        scientific/targets/

    FG-ML
        scientific/features/
        scientific/ml/
        scientific/evaluation/

    FG-API
        backend/

    FG-UI
        frontend/

    FG-QA
        tests/

Agents should not modify another agent's subsystem without coordination.

---

# 349. NO SIMULTANEOUS EDITING

Two agents should not independently modify the same files at the same time.

If cross-boundary changes are required:

    identify dependency
        |
        v
    coordinate
        |
        v
    implement
        |
        v
    integration review

This prevents merge conflicts and inconsistent architecture.

---

# 350. AGENT INSTRUCTIONS

Each agent should receive:

    task objective
    allowed files
    prohibited files
    input/output contracts
    tests required
    acceptance criteria
    scientific constraints

This should be explicit.

---

# 351. AI-GENERATED SCIENCE RULE

AI agents may propose:

- hypotheses,
- implementations,
- feature ideas,
- tests,
- documentation.

But they must not invent:

- scientific results,
- dataset availability,
- forecast skill,
- validation metrics,
- causal explanations,
- operational guarantees.

All scientific claims require evidence.

---

# 352. CODE REVIEW CHECKLIST

Every substantial pull request should be reviewed for:

    correctness
    tests
    maintainability
    security
    performance
    API compatibility
    scientific assumptions
    leakage
    reproducibility

---

# 353. SCIENCE AUDITOR CHECKLIST

The science auditor should ask:

    Is the forecast/observation pairing physically correct?

    Are timestamps correct?

    Are accumulation windows correct?

    Is the spatial grid handled correctly?

    Is future information leaking?

    Is the baseline competitive?

    Are results calibrated?

    Are claims supported by measured evidence?

    Are regional/seasonal limitations documented?

---

# 354. UI AUDITOR CHECKLIST

The UI auditor should ask:

    Is the primary reliability state immediately visible?

    Can an operator identify WHERE risk exists?

    Can they identify WHEN risk changes?

    Can they understand WHY?

    Is evidence quality visible?

    Are unavailable values handled honestly?

    Is the interface simple enough for operational use?

    Is advanced scientific detail available without cluttering the main screen?

---

# 355. PERFORMANCE PRINCIPLE

Performance optimization should happen after correctness.

Priority:

    scientific correctness
        >
    data integrity
        >
    API correctness
        >
    UI correctness
        >
    optimization

Do not optimize an incorrect scientific pipeline.

---

# 356. LARGE-DATA STRATEGY

As data volume increases:

    raw GRIB
        |
        v
    processed Zarr
        |
        v
    feature Parquet
        |
        v
    metadata PostgreSQL

The browser should never receive unnecessary raw multidimensional forecast fields.

---

# 357. CACHING

Caching may be introduced for expensive repeated queries.

Potential cache targets:

    current forecast summaries
    map tiles
    reliability trajectories
    frequently accessed historical cases

Caching must never cause stale scientific data to appear as current.

Every cached result should have a validity/creation timestamp.

---

# 358. ASYNCHRONOUS PROCESSING

Long-running jobs should not block API requests.

Potential asynchronous tasks:

    forecast ingestion
    GRIB conversion
    regridding
    verification
    feature generation
    model inference for large domains
    historical replay preparation

The exact queue/worker technology can be chosen later.

---

# 359. MVP BOUNDARY

The first real MVP should not attempt to implement every planned module.

Minimum scientifically meaningful MVP:

    real NCMRWF/TIGGE forecast
        +
    real observation
        +
    exact alignment
        +
    verification
        +
    bust definition
        +
    climatology baseline
        +
    simple ML baseline
        +
    basic reliability output
        +
    map
        +
    trajectory
        +
    historical replay

This is already a legitimate scientific system.

---

# 360. MVP SUCCESS TEST

The MVP should answer:

> Given a historical NCMRWF forecast at a particular lead time, can ForecastGuard estimate whether that forecast is likely to experience a meaningful future error, and can we later verify whether the warning was correct?

If this cannot be answered using real data, the system is not ready for advanced modules.

---

# 361. IMPLEMENTATION ROADMAP

The implementation should proceed through controlled milestones.

### M0 — Repository bootstrap

Create:

    repository
    Python environment
    frontend project
    Docker setup
    CI skeleton
    documentation structure

No scientific claims yet.

---

### M1 — Data reality check

Implement:

    TIGGE access
    GRIB parsing
    metadata extraction
    QC
    D0 dataset

Success:

    real NCMRWF forecast fields successfully validated.

---

### M2 — Observation integration

Implement:

    observation ingestion
    observation QC
    timestamp alignment
    spatial alignment

Success:

    forecast-observation pairs are physically compatible.

---

### M3 — Verification Atlas

Implement:

    MAE
    RMSE
    bias
    spatial error
    event metrics
    preliminary bust severity
    maps

Success:

    real historical forecast errors can be inspected.

---

### M4 — Baseline Predictor

Implement:

    climatology
    persistence/run-to-run baseline
    spread-only baseline
    logistic regression
    tree-based model

Success:

    first defensible bust-probability model.

---

### M5 — Ensemble Intelligence

Implement:

    spread
    spread growth
    divergence
    clustering
    branch structure

Success:

    determine whether ensemble geometry adds value beyond spread.

---

### M6 — Forecast Trajectory

Implement:

    forecast-cycle sequences
    run-to-run evolution
    trajectory features
    trajectory similarity

Success:

    test the path-dependence hypothesis.

---

### M7 — Historical Memory

Implement:

    atmospheric analogues
    forecast-trajectory analogues
    failure pathway retrieval

Success:

    determine whether historical trajectories improve early warning.

---

### M8 — Multi-Model Intelligence

Implement:

    model similarity
    model disagreement
    model-relative NCMRWF divergence
    graph representation

Success:

    determine whether cross-model information improves reliability prediction.

---

### M9 — Regime / OOD

Implement:

    atmospheric embedding
    regime detection
    novelty score
    evidence-quality interaction

Success:

    determine whether regime/OOD improves calibration or selective prediction.

---

### M10 — Fragility

Implement experimental:

    ensemble-based fragility proxy

Success:

    keep only if validated.

---

### M11 — Fusion + Calibration

Implement:

    final feature fusion
    calibration
    risk trajectory
    hazard
    evidence quality
    abstention where justified

Success:

    stable calibrated operational output.

---

### M12 — Backend

Implement:

    FastAPI
    schemas
    database
    services
    scientific result APIs
    alert APIs

Success:

    frontend can consume validated outputs.

---

### M13 — ForecastGuard Dashboard

Implement:

    operational dashboard
    India map
    reliability
    bust risk
    trajectory
    evidence
    alerts
    model information

Success:

    operator can understand current reliability quickly.

---

### M14 — Replay / Autopsy

Implement:

    historical case selection
    time-machine replay
    forecast vs observation
    alert history
    failure fingerprint
    autopsy

Success:

    complete real-data story can be demonstrated.

---

### M15 — Blind Evaluation

Lock:

    features
    model
    calibration
    thresholds

Run:

    unseen historical test set

Success:

    final scientific claims are based on untouched data.

---

# 362. DEVELOPMENT GATES

Do not advance purely because the calendar says so.

Advance only when the current milestone passes its gate.

Example:

    M1
    data valid?
        |
       YES
        ↓
    M2

If:

    NO

then remain at M1.

This prevents building sophisticated ML on top of incorrect data.

---

# 363. FIRST BUILD TARGET

The immediate implementation target is:

    M0 → M1

Specifically:

    repository
        +
    TIGGE access
        +
    real NCMRWF data
        +
    GRIB inspection
        +
    metadata validation
        +
    small D0 dataset

Do not begin by building the final dashboard.

The dashboard should eventually visualize verified science.

---

# 364. DEFINITION OF DONE — M1

M1 is complete only when the team can demonstrate:

    ✓ real NCMRWF/TIGGE data obtained through an authorized route
    ✓ source metadata recorded
    ✓ GRIB2 parsed successfully
    ✓ forecast cycles identified
    ✓ lead times identified
    ✓ ensemble members identified
    ✓ spatial grid verified
    ✓ units verified
    ✓ precipitation accumulation semantics verified
    ✓ QC report generated
    ✓ immutable/raw provenance preserved

---

# 365. DEFINITION OF DONE — M2

M2 is complete only when:

    ✓ observation source is documented
    ✓ observation timestamps are understood
    ✓ forecast windows are aligned
    ✓ observation windows are aligned
    ✓ spatial grids are reconciled
    ✓ missing values are handled
    ✓ matched forecast-observation pairs are reproducible
    ✓ leakage boundary is documented

---

# 366. DEFINITION OF DONE — M3

M3 is complete only when:

    ✓ error fields are produced
    ✓ scalar metrics are produced
    ✓ regional metrics are produced
    ✓ lead-time behaviour is visible
    ✓ preliminary bust distribution is known
    ✓ failure cases can be inspected
    ✓ verification is independent of ML

---

# 367. DEFINITION OF DONE — M4+

For every subsequent ML milestone:

    baseline exists
    hypothesis exists
    leakage audit exists
    experiment exists
    validation exists
    calibration evaluated
    warning performance evaluated
    generalization evaluated
    keep/kill decision documented

---

# 368. PROJECT BOARD

The project board should organize work by:

    BACKLOG
    READY
    IN PROGRESS
    REVIEW
    SCIENCE AUDIT
    TESTING
    DONE
    BLOCKED

Scientific tasks should not be marked DONE merely because code executes.

---

# 369. ISSUE TEMPLATE

Scientific feature issues should contain:

    Problem
    Hypothesis
    Proposed Method
    Baseline
    Data Required
    Leakage Risk
    Evaluation Metrics
    Expected Output
    Kill Condition
    Acceptance Criteria

---

# 370. BUG TEMPLATE

Scientific/data bugs should contain:

    observed behaviour
    expected behaviour
    affected dataset
    affected forecast cycle
    reproduction steps
    scientific impact
    fix
    regression test

---

# 371. DOCUMENTATION STRUCTURE

The docs directory should eventually contain:

    docs/
        architecture/
        data/
        science/
        api/
        frontend/
        deployment/
        experiments/
        validation/
        operations/

Important scientific decisions should be documented rather than left only in chat messages.

---

# 372. ARCHITECTURE DECISION RECORDS

Major architectural decisions should be recorded as ADRs.

Examples:

    ADR-001 scientific storage
    ADR-002 database architecture
    ADR-003 verification grid
    ADR-004 model baseline
    ADR-005 calibration strategy
    ADR-006 API versioning

Each ADR should explain:

    context
    decision
    alternatives
    consequences

---

# 373. SCIENTIFIC DECISION RECORDS

Scientific choices should also be documented.

Examples:

    bust definition
    precipitation accumulation handling
    regridding method
    analogue distance
    ensemble clustering method
    calibration method
    alert threshold

The purpose is reproducibility and defensibility.

---

# 374. SIH DEMONSTRATION BUILD

The SIH build should ultimately include three layers:

### Layer 1 — Operational

    "What should I worry about?"

### Layer 2 — Scientific

    "Why is ForecastGuard worried?"

### Layer 3 — Verification

    "Was ForecastGuard right?"

This three-layer structure should be visible in the final demonstration.

---

# 375. JUDGE DEFENSIBILITY

A judge should be able to ask:

> Is this real data?

Answer:

    Yes, where access permits, the system uses authorized real forecast and observational datasets.

> Is the bust probability fake?

Answer:

    No. It is generated by a calibrated model trained and evaluated on historical forecast-verification data.

> How do you know it works?

Answer:

    We compare against climatology and conventional baselines on chronological unseen test periods.

> Does the fancy AI actually help?

Answer:

    We perform ablation and kill-or-keep experiments.

> What if the model doesn't know?

Answer:

    ForecastGuard can expose insufficient evidence/OOD rather than manufacturing certainty.

> Is this another weather forecast?

Answer:

    No. It is a reliability layer over an existing forecast.

---

# 376. ANTI-HYPE RULE

The project presentation must avoid unsupported phrases such as:

    100% accurate
    predicts every bust
    solves weather uncertainty
    revolutionary
    world-first
    guaranteed early warning

Prefer evidence-based language:

    calibrated
    validated
    historically evaluated
    incremental skill
    earlier warning
    uncertainty-aware
    evidence-aware
    operationally focused

---

# 377. FINAL ENGINEERING PRINCIPLE

The repository should make it difficult to do the wrong thing.

Good architecture should naturally encourage:

    reproducibility
    validation
    provenance
    testing
    modularity
    scientific honesty

The system should make it easy to trace:

    dashboard number
        ↓
    API response
        ↓
    model output
        ↓
    feature vector
        ↓
    forecast data
        ↓
    source file

---

# 378. FINAL BUILD PRINCIPLE

The team should not attempt to "finish ForecastGuard" in one giant coding sprint.

Instead:

    BUILD SMALL
        ↓
    VERIFY
        ↓
    MEASURE
        ↓
    LEARN
        ↓
    EXPAND

Every layer should earn the right to exist.

---

# 379. CURRENT NEXT ACTION

After this architecture is locked, the next practical step is not another theoretical module.

The next action is:

    CREATE THE REPOSITORY
        ↓
    CREATE M0 STRUCTURE
        ↓
    VERIFY LOCAL ENVIRONMENT
        ↓
    CONFIGURE DATA ACCESS
        ↓
    OBTAIN THE FIRST REAL D0 NCMRWF/TIGGE SAMPLE
        ↓
    INSPECT THE ACTUAL GRIB2
        ↓
    BUILD THE FIRST QC REPORT

Only after this succeeds should the team begin building the verification engine.

---

# 380. FINAL PROJECT RULE

ForecastGuard should always follow:

    REAL DATA
        →
    CORRECT SCIENCE
        →
    VALIDATED MODEL
        →
    CALIBRATED RISK
        →
    SIMPLE OPERATIONAL INTERFACE
        →
    OBJECTIVE VERIFICATION

That chain is the foundation of the entire project.
# CHUNK 10 — M0 REPOSITORY BOOTSTRAP AND FIRST REAL-DATA BUILD

## 381. M0 OBJECTIVE

M0 is the first implementation milestone.

The objective is not to build the ForecastGuard dashboard.

The objective is to create a clean, reproducible development environment and successfully process the first small sample of real NCMRWF/TIGGE data.

M0 must establish:

    repository
        +
    development environment
        +
    scientific environment
        +
    backend skeleton
        +
    frontend skeleton
        +
    database
        +
    data-access configuration
        +
    testing infrastructure
        +
    first real forecast sample

---

# 382. M0 SUCCESS CONDITION

M0 is successful when the team can execute a documented command sequence that results in:

    real NCMRWF/TIGGE forecast data
        ↓
    GRIB2 file
        ↓
    parser
        ↓
    metadata inspection
        ↓
    QC report
        ↓
    reproducible artifact

No ML model is required for M0.

No forecast-bust probability is required for M0.

No final UI is required for M0.

---

# 383. INITIAL REPOSITORY

Create:

    forecastguard/

The initial repository should contain:

    forecastguard/
    │
    ├── backend/
    ├── frontend/
    ├── scientific/
    ├── data/
    ├── configs/
    ├── scripts/
    ├── tests/
    ├── docs/
    ├── infra/
    ├── notebooks/
    ├── experiments/
    ├── .github/
    ├── .gitignore
    ├── .env.example
    ├── docker-compose.yml
    ├── Makefile
    ├── README.md
    └── LICENSE

---

# 384. DATA DIRECTORY

The data directory must distinguish raw and derived data.

Conceptually:

    data/
    ├── raw/
    │   ├── tigge/
    │   └── observations/
    │
    ├── interim/
    │
    ├── processed/
    │
    ├── features/
    │
    └── manifests/

Raw source files should not be modified in place.

---

# 385. GITIGNORE

The `.gitignore` must exclude:

    .env
    __pycache__/
    *.pyc
    .pytest_cache/
    .mypy_cache/
    .ruff_cache/
    node_modules/
    .next/
    build/
    dist/
    data/raw/
    data/interim/
    data/processed/
    data/features/
    logs/
    *.log

Large scientific data must not accidentally enter Git.

Small metadata manifests may be committed.

---

# 386. ENVIRONMENT FILE

Create:

    .env.example

It should contain variable names only.

Conceptual configuration:

    DATABASE_URL=
    ECDS_API_URL=
    ECDS_API_KEY=
    STORAGE_ROOT=

No real credentials may be committed.

The actual `.env` file remains local.

---

# 387. PYTHON ENVIRONMENT

The scientific/backend environment should use a supported Python version selected for compatibility with:

- FastAPI,
- Pydantic,
- xarray,
- eccodes,
- cfgrib,
- NumPy,
- pandas,
- scikit-learn,
- XGBoost/LightGBM where used.

Dependency versions should be pinned or constrained sufficiently for reproducibility.

---

# 388. INITIAL PYTHON DEPENDENCIES

The initial scientific environment should prioritize only dependencies needed for M0/M1.

Potential initial dependencies:

    fastapi
    uvicorn
    pydantic
    pydantic-settings
    numpy
    pandas
    xarray
    scipy
    scikit-learn
    eccodes
    cfgrib
    netcdf4
    pyarrow
    pyyaml
    requests/httpx
    pytest
    pytest-cov
    ruff
    mypy

Additional dependencies should be introduced only when required.

Do not install every planned ML/visualization library on day one.

---

# 389. CDS / ECDS ACCESS

TIGGE access must use the currently authorized ECMWF data-access mechanism.

The team must verify the current ECDS access procedure before implementing automated retrieval.

Do not blindly copy old TIGGE WEB-API examples into the production system.

The system should store:

    ECDS API URL
    dataset name
    authentication configuration
    retrieval configuration

outside source code.

---

# 390. ECDS DATASET CONFIGURATION

The initial configuration should represent:

    dataset:
        tigge-forecasts

    centre:
        dems

    forecast:
        NCMRWF

    cycle:
        00 UTC

    variable:
        tp

    forecast type:
        perturbed ensemble forecast

    domain:
        India-focused subset where supported/appropriate

    lead:
        initial small range

The actual retrieval request must be generated from the current ECDS catalogue/form and verified against the returned file.

---

# 391. FIRST DOWNLOAD RULE

Do not immediately request a large historical archive.

The first request should be the smallest useful real sample.

The goal is:

    obtain one valid real file
        ↓
    inspect it
        ↓
    verify semantics
        ↓
    automate safely

This avoids wasting time, bandwidth and storage because of an incorrect request.

---

# 392. REQUEST VERIFICATION

Before running a large retrieval, inspect the generated request and confirm:

    centre = dems
    dataset = TIGGE
    forecast type = intended ensemble type
    variable = tp
    initialization cycle = intended cycle
    date = intended historical date
    forecast steps = intended steps

Do not assume an API request means the returned file contains exactly what was intended.

Always inspect the result.

---

# 393. API CREDENTIAL SAFETY

Credentials must:

    never be committed
    never be hardcoded
    never appear in notebooks
    never appear in logs
    never appear in screenshots
    never be pasted into public repositories

If credentials are accidentally exposed, rotate/revoke them.

---

# 394. INGESTION MANIFEST

Every downloaded file should receive a manifest entry.

Example conceptual record:

    source
    dataset
    centre
    retrieval_time
    requested_date
    requested_cycle
    requested_variables
    requested_steps
    local_path
    checksum
    file_size
    status

The manifest becomes part of the provenance chain.

---

# 395. RAW FILE NAMING

Raw files should have deterministic names.

Conceptual:

    dems_tp_pf_YYYYMMDD_00.grib2

If multiple files are required, include additional identifiers.

The filename should not be the sole source of truth; metadata inside the GRIB must also be inspected.

---

# 396. GRIB INSPECTION COMMAND

The first diagnostic should inspect the GRIB contents before scientific processing.

Potential tooling:

    eccodes / grib_ls
    cfgrib
    xarray

The inspection should report:

    centre
    variable
    typeOfLevel
    forecast type
    date
    time
    step
    member
    units
    grid
    dimensions

---

# 397. FIRST GRIB INSPECTION REPORT

Generate a machine-readable and human-readable report.

For example:

    reports/
        d0_grib_inspection.json
        d0_grib_inspection.txt

The report should contain:

    file identity
    message count
    variable inventory
    member inventory
    lead-time inventory
    grid information
    units
    missing values
    warnings

---

# 398. MEMBER VALIDATION

The system must not assume the expected number of ensemble members.

Instead:

    inspect actual returned members
        ↓
    record them
        ↓
    compare against expected catalogue metadata
        ↓
    flag discrepancies

If a member is missing:

    status = PARTIAL

not:

    silently ignore

---

# 399. LEAD-TIME VALIDATION

The system should enumerate actual available forecast steps.

For example:

    step 0
    step 6
    step 12
    ...

or the actual returned schedule.

Do not infer available lead times from documentation alone.

The file itself is authoritative for what was actually retrieved.

---

# 400. VARIABLE VALIDATION

For the initial precipitation experiment:

    shortName
    paramId
    units

must be checked.

The system must verify that the retrieved field corresponds to the intended total precipitation quantity.

---

# 401. ACCUMULATION VALIDATION

Before any verification:

    inspect step
    inspect startStep
    inspect endStep
    inspect units
    inspect accumulation semantics

Document the interpretation.

Do not assume:

    step = accumulation window

without confirming the GRIB metadata.

---

# 402. GRID VALIDATION

Record:

    grid type
    Ni
    Nj
    latitude range
    longitude range
    spacing
    scan direction
    coordinate ordering

This information is required before regridding or spatial verification.

---

# 403. COORDINATE NORMALIZATION

The parser should normalize coordinates into a predictable internal representation.

For example:

    latitude increasing/decreasing
    longitude convention
    dimension order

The original grid definition must remain available in provenance metadata.

---

# 404. MISSING VALUE HANDLING

Missing values must be explicitly represented.

Never silently convert:

    missing → 0

For precipitation, this distinction is particularly dangerous because zero rainfall is a valid physical value.

---

# 405. DATA QC REPORT

The first QC report should contain:

    file status
    metadata status
    timestamp status
    lead-time status
    member status
    coordinate status
    units status
    missing-value status
    physical-range status
    duplicate status

Overall result:

    PASS
    WARN
    FAIL

---

# 406. QC SEVERITY

Not every anomaly should stop processing.

Use categories such as:

    INFO
    WARNING
    ERROR
    FATAL

Examples:

    unexpected metadata field
        =
    WARNING

    missing required forecast member
        =
    ERROR / PARTIAL

    unreadable GRIB
        =
    FATAL

The exact severity should be documented.

---

# 407. SCIENTIFIC DATA OBJECT

After parsing, the internal scientific representation should contain:

    field
    coordinates
    dimensions
    metadata
    source_reference
    forecast_initialization
    valid_time
    lead_time
    member
    variable
    units

This object should be independent of the API layer.

---

# 408. DATA PROVENANCE

Every processed object should retain:

    source file
    checksum
    source dataset
    dataset version
    retrieval timestamp
    parser version
    preprocessing version

This allows later reconstruction.

---

# 409. FIRST SCIENTIFIC STORAGE FORMAT

The first small sample may remain in a convenient form while the pipeline is being validated.

Once the schema is stable, convert appropriate multidimensional data into:

    Zarr

The exact chunking strategy should be based on actual access patterns.

Do not optimize chunking before measuring workload.

---

# 410. PARQUET OUTPUT

Metadata and tabular QC information should use:

    Parquet

Potential tables:

    forecast_manifest.parquet
    forecast_metadata.parquet
    qc_results.parquet

---

# 411. DATABASE BOOTSTRAP

PostgreSQL/PostGIS should be initialized through Docker.

The initial database should store metadata rather than huge forecast arrays.

Potential initial tables:

    forecast_runs
    forecast_fields
    dataset_registry
    ingestion_jobs
    qc_results

---

# 412. INITIAL DATABASE ENTITY — FORECAST RUN

Conceptual fields:

    id
    centre
    model
    model_version
    initialization_time
    cycle
    dataset_version
    ingestion_status
    created_at

---

# 413. INITIAL DATABASE ENTITY — FORECAST FIELD

Conceptual fields:

    id
    forecast_run_id
    variable
    level
    forecast_type
    member
    lead_time
    valid_time
    units
    storage_reference
    checksum

---

# 414. INITIAL DATABASE ENTITY — INGESTION JOB

Conceptual fields:

    id
    dataset
    request_reference
    started_at
    completed_at
    status
    error_message
    artifact_reference

---

# 415. DATABASE MIGRATIONS

Database schema changes should use migrations.

Do not manually modify production database schemas without recording the change.

The migration tool can be selected during implementation.

---

# 416. FASTAPI BOOTSTRAP

The initial API should expose only basic health and metadata endpoints.

Example:

    GET /api/v1/health

    GET /api/v1/forecasts

    GET /api/v1/forecasts/{forecast_id}

Scientific risk endpoints should not exist until real scientific outputs exist.

---

# 417. HEALTH ENDPOINT

Health checks should distinguish:

    API healthy
    database healthy
    scientific storage reachable

A healthy API must not imply that forecast data are available.

---

# 418. FRONTEND BOOTSTRAP

The initial frontend should only establish:

    application shell
    routing
    visual theme
    API client
    basic health/status page

Do not build the final dashboard before M1/M2 scientific outputs exist.

---

# 419. INITIAL FRONTEND ROUTES

Conceptually:

    /
        landing / operational shell

    /dashboard
        future operational dashboard

    /replay
        future replay interface

    /autopsy
        future autopsy interface

    /research
        future research mode

Only the shell needs to be functional initially.

---

# 420. DESIGN SYSTEM BOOTSTRAP

The initial UI design system should establish:

    typography
    spacing
    cards
    buttons
    badges
    status indicators
    navigation
    map container
    chart container

The ForecastGuard visual language should use the approved dark operational aesthetic.

---

# 421. DOCKER COMPOSE

The initial local environment should provide:

    postgres
    backend
    frontend

A scientific worker can be added when asynchronous scientific jobs become necessary.

---

# 422. DATABASE PERSISTENCE

Docker volumes should preserve local PostgreSQL data.

Do not place large scientific datasets inside the PostgreSQL container.

---

# 423. SCIENTIFIC WORKER

Initially, scientific scripts may run directly from the development environment.

Later, introduce a dedicated scientific worker when jobs become long-running.

Potential responsibilities:

    ingestion
    preprocessing
    verification
    feature generation
    model inference

---

# 424. FIRST COMMAND CONTRACT

The project should eventually support a workflow conceptually similar to:

    git clone ...
    cd forecastguard
    copy .env.example → .env
    configure credentials
    docker compose up
    run D0 ingestion
    run GRIB inspection
    run QC

Exact command syntax can be finalized during implementation.

---

# 425. M0 COMMANDS

Provide simple commands such as:

    make setup
    make up
    make down
    make test
    make lint
    make inspect-d0
    make qc-d0

These should invoke documented scripts rather than require users to remember long commands.

---

# 426. FIRST SCRIPT SET

Create only the scripts required for M0.

Conceptually:

    scripts/
        download/
            fetch_tigge.py

        inspect/
            inspect_grib.py

        qc/
            qc_forecast.py

        reports/
            generate_d0_report.py

Do not create dozens of empty scripts merely to match the final architecture.

---

# 427. FIRST SCIENTIFIC MODULE SET

Create only:

    scientific/
        ingestion/
        parsing/
        qc/

The following should remain mostly empty until their milestones:

    verification
    features
    ml
    analogues
    multimodel
    regimes
    ood

The architecture can exist without pretending those modules are implemented.

---

# 428. FIRST TEST SET

M0 tests should cover:

    configuration loading
    manifest generation
    deterministic file identity
    GRIB metadata parsing
    coordinate normalization
    member detection
    lead-time detection
    missing-value detection
    QC result generation

---

# 429. FIXTURE POLICY

Do not place large real forecast files into the repository.

Instead, maintain:

    tiny synthetic GRIB fixture
    or
    minimal test artifact

where licensing and technical feasibility permit.

Real data tests should run against externally available/local data artifacts.

---

# 430. SYNTHETIC GRIB TEST

A synthetic/minimal GRIB fixture should test:

    parser works
    metadata extracted
    coordinates recognized
    timestamps parsed
    member information handled

This is a software test only.

It is not a scientific result.

---

# 431. REAL DATA SMOKE TEST

A separate smoke test should operate on an actual authorized NCMRWF/TIGGE file.

It should verify:

    file opens
    intended variable exists
    intended forecast cycle exists
    members are discoverable
    lead times are discoverable
    grid is valid
    units are valid

---

# 432. M0 ACCEPTANCE REPORT

At the end of M0, generate:

    docs/reports/m0_data_reality_check.md

It should answer:

    What dataset was requested?

    What exact file was returned?

    What metadata were observed?

    Which members were present?

    Which lead times were present?

    What grid was returned?

    What units were returned?

    What are the accumulation semantics?

    What problems were encountered?

    What remains uncertain?

---

# 433. NO ASSUMPTION POLICY

If the actual downloaded file contradicts an assumption in this architecture:

    trust the actual verified file

and update the architecture/documentation.

The architecture is a plan.

The data are the reality.

---

# 434. M0 STOP CONDITIONS

Stop and investigate if:

    authentication fails
    file is empty
    file cannot be parsed
    unexpected centre appears
    unexpected variable appears
    ensemble members are missing
    lead times differ unexpectedly
    grid is unexpected
    units are unexpected
    precipitation semantics remain unclear

Do not proceed to verification while these issues remain unresolved.

---

# 435. FIRST REAL-DATA MISSION

The immediate mission after repository bootstrap is:

    Obtain one small authorized NCMRWF/TIGGE sample.

Then:

    inspect it.

Then:

    report exactly what is inside.

Then:

    build the parser/QC around the observed structure.

Do not begin by assuming the file structure from documentation.

---

# 436. M0 DELIVERABLES

Required deliverables:

    repository initialized
    Python environment
    frontend environment
    Docker environment
    PostgreSQL/PostGIS
    environment configuration
    scientific module skeleton
    backend skeleton
    frontend shell
    tests
    data manifest
    real NCMRWF/TIGGE sample
    GRIB inspection report
    QC report
    M0 data-reality document

---

# 437. M0 NON-DELIVERABLES

Do not require:

    final ML model
    bust probability
    calibrated risk
    ensemble clustering
    multi-model graph
    OOD
    fragility
    final map
    final dashboard
    SIH demo

Those belong to later milestones.

---

# 438. M0 QUALITY GATE

M0 passes only if:

    ✓ repository is reproducible
    ✓ secrets are protected
    ✓ services start successfully
    ✓ backend starts
    ✓ frontend starts
    ✓ database starts
    ✓ tests pass
    ✓ real NCMRWF/TIGGE data is obtained through an authorized method
    ✓ GRIB can be parsed
    ✓ metadata are recorded
    ✓ QC report is generated
    ✓ unresolved scientific assumptions are documented

---

# 439. IMMEDIATE NEXT STEP AFTER M0

Once M0 passes:

    M1 — DATA REALITY / INGESTION HARDENING

Then:

    M2 — OBSERVATION INTEGRATION

Then:

    M3 — VERIFICATION ATLAS

Only after M3 should ForecastGuard have enough verified historical data to seriously train and evaluate the first bust predictor.

---

# 440. PROJECT DEVELOPMENT RULE

From this point forward, every implementation request should identify:

    milestone
    subsystem
    files affected
    dependencies
    acceptance criteria
    tests
    scientific risks

This keeps implementation controlled.

---

# 441. AI CODING RULE

When asking an AI coding agent to implement a subsystem, provide the agent with:

    exact task
    repository context
    allowed directories
    forbidden modifications
    interfaces
    acceptance tests
    scientific constraints

The agent should return:

    implementation
    tests
    documentation
    known limitations

It should not silently change project architecture.

---

# 442. COMPLETE-FILE PREFERENCE

When implementation begins, production files should generally be provided as complete replacement-ready files when practical.

Avoid forcing a beginner developer to manually merge many tiny code fragments.

The final project should remain copy-pasteable and reproducible.

---

# 443. HUMAN REVIEW REQUIREMENT

No AI-generated scientific code should be accepted merely because:

    it runs

Acceptance requires:

    code correctness
    tests
    scientific reasoning
    leakage review
    reproducibility
    human approval

---

# 444. M0 FINAL PRINCIPLE

The first victory is not a beautiful dashboard.

The first victory is:

> We obtained real NCMRWF forecast data, understood exactly what it contains, preserved its provenance, and can process it reproducibly.

Once that works, everything else has a trustworthy foundation.

---

# 445. TRANSITION TO IMPLEMENTATION

After Chunk 10 is locked, stop expanding the architecture document unless a genuine implementation discovery requires an architectural change.

The next work should happen in the repository itself.

The immediate implementation sequence is:

    CREATE REPOSITORY
        ↓
    BOOTSTRAP ENVIRONMENT
        ↓
    VERIFY DOCKER / PYTHON / NODE
        ↓
    CONFIGURE ECDS ACCESS
        ↓
    DOWNLOAD ONE SMALL REAL TIGGE SAMPLE
        ↓
    INSPECT GRIB2
        ↓
    VALIDATE MEMBERS / LEADS / GRID / UNITS
        ↓
    WRITE D0 QC
        ↓
    PRODUCE M0 REPORT
        ↓
    PASS M0