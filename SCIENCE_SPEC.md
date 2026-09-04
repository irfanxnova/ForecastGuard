# ForecastGuard Scientific Specification

## 1. PURPOSE

ForecastGuard is an AI-based forecast reliability intelligence system
for SIH2026 Problem Statement SIH26079.

Its purpose is to estimate how vulnerable an existing medium-range NWP
forecast is to significant future forecast failure.

ForecastGuard does NOT generate a replacement weather forecast.

It evaluates the reliability of an existing forecast.

Core principle:

NWP tells us what may happen.

ForecastGuard tells us how much we should trust that forecast.

The primary scientific question is:

> How early can ForecastGuard reliably detect an upcoming forecast bust?

---

# 2. SCIENTIFIC FRAMING

Forecast failure must be treated as a dynamic process rather than only
as a static binary classification problem.

A forecast may evolve through states such as:

STABLE
→ WATCH
→ DEGRADING
→ HIGH RISK
→ VERIFIED FAILURE

These states must NOT be assumed to be scientifically real beforehand.

If such states are used by the system, their usefulness must be
validated using historical data.

The system should investigate the trajectory toward failure.

Conceptually:

P(failure | current state, forecast history)

rather than only:

P(failure | current state)

---

# 3. REAL DATA REQUIREMENT

The scientific system must ultimately operate on real meteorological
data.

Potential sources include:

- NCMRWF forecasts
- TIGGE forecasts
- ensemble forecasts
- IMD observations
- IMD-NCMRWF merged rainfall analysis
- atmospheric state/reanalysis datasets
- other authorized forecast and observation datasets

Simulated data may be used during software development and UI
development.

Simulated data must NEVER be presented as:

- real NCMRWF forecasts
- real observations
- real historical cases
- measured model performance
- actual forecast accuracy

---

# 4. FORECAST SOURCE

The primary forecast target is NCMRWF medium-range NWP.

Where appropriate, NCMRWF forecasts may be obtained through TIGGE.

Relevant metadata must be preserved.

Examples:

- forecast initialization time
- valid time
- lead time
- model/centre
- model version or upgrade era when available
- ensemble member
- variable
- pressure/surface level
- grid
- units
- accumulation semantics

Do not discard metadata that may affect scientific interpretation.

---

# 5. OBSERVATION SOURCE

Initial verification should prioritize precipitation because it provides
a spatially structured and operationally meaningful forecast-error
problem.

Where available, IMD-NCMRWF merged rainfall analysis may be used as the
verification reference.

The observation dataset and forecast dataset must be temporally and
spatially aligned before verification.

---

# 6. TEMPORAL ALIGNMENT

Temporal alignment is non-negotiable.

Forecast valid periods and observation periods must represent the same
physical time window.

For accumulated variables such as precipitation, the accumulation
semantics must be explicitly verified.

Never compare:

forecast accumulation window A

against

observation window B

unless the mismatch is scientifically intentional and documented.

Forecast initialization time, forecast step, valid time and observation
window must be traceable.

---

# 7. SPATIAL ALIGNMENT

Forecast and observation grids may differ.

A scientifically justified regridding procedure must be applied before
comparison.

The system must record:

- source grid
- target grid
- regridding method
- interpolation/regridding assumptions
- missing-value handling
- land/sea treatment where relevant

Do not silently change grids.

---

# 8. FORECAST BUST DEFINITION

Forecast bust must NOT be defined using one arbitrary universal RMSE
threshold.

Forecast failure should consider multiple dimensions.

Potential dimensions include:

1. Error magnitude
2. Spatial displacement
3. Timing error
4. Event miss
5. False alarm
6. Structural/spatial-pattern error
7. Climatology-normalized difficulty

The exact thresholds must be empirically justified using the dataset
and documented.

---

# 9. ERROR MAGNITUDE

Possible continuous verification measures include:

- MAE
- RMSE
- bias
- normalized error
- anomaly-based error

Continuous error should be preserved even when a discrete bust label is
created.

Do not throw away information by converting everything immediately
into TRUE/FALSE.

---

# 10. SPATIAL ERROR

Forecasts can fail because an event occurs in the wrong location even
when average intensity appears reasonable.

Where scientifically appropriate, evaluate:

- displacement
- spatial overlap
- pattern similarity
- object/event displacement
- spatial correlation

The chosen metric must match the phenomenon being evaluated.

---

# 11. TIMING ERROR

Forecast failure may occur because an event is predicted too early or
too late.

Where appropriate, estimate:

- event onset difference
- peak timing difference
- duration difference
- temporal displacement

Timing must be evaluated using clearly defined event criteria.

---

# 12. EVENT FAILURE

For event-oriented verification, consider:

### Miss

A significant observed event was not adequately forecast.

### False alarm

A significant forecast event did not occur as forecast.

Event thresholds must be defined before evaluation and must not be
chosen after inspecting test results.

---

# 13. FAILURE FINGERPRINT

A forecast failure should eventually be represented by a failure
fingerprint.

Possible dimensions:

- location
- timing
- intensity
- event miss/false alarm
- spatial structure

The purpose is to answer:

> HOW did the forecast fail?

A single scalar error score is insufficient to fully describe failure
morphology.

---

# 14. CLIMATOLOGY NORMALIZATION

Forecast difficulty depends on:

- region
- season
- lead time
- variable
- event type

Therefore, where appropriate, errors should be normalized relative to
historical behaviour.

A forecast error should be considered unusually large only relative to
an appropriate reference population.

Do not assume that one raw error threshold has the same meaning
everywhere.

---

# 15. FORECAST TRAJECTORY

A major research hypothesis is that forecast failure may depend on the
trajectory of the forecast rather than only its current state.

A trajectory may include:

- successive forecast cycles
- lead-time evolution
- ensemble evolution
- changes in uncertainty
- changes in model agreement
- atmospheric-state evolution

The system must test whether trajectory information provides predictive
value beyond simpler current-state features.

---

# 16. PATH DEPENDENCE HYPOTHESIS

Hypothesis:

Two cases can have similar current forecast states but different
forecast histories.

If their future failure probabilities differ meaningfully, this
supports path dependence.

Conceptually:

P(B | X, H_A) != P(B | X, H_B)

where:

X = current forecast state

H = forecast history

This is a hypothesis to test, not an assumed scientific fact.

---

# 17. TRAJECTORY INCREMENTAL VALUE

Compare progressively:

1. Climatology
2. Current-state features
3. Current-state + persistence
4. Current-state + run-to-run changes
5. Current-state + ensemble dynamics
6. Forecast trajectory representation

The trajectory representation must demonstrate incremental predictive
value before being considered scientifically useful.

If it provides no meaningful improvement, remove it.

---

# 18. ENSEMBLE INTELLIGENCE

Do not reduce ensemble information to spread alone.

Potential ensemble features include:

- mean
- spread
- variance
- percentiles
- skewness
- member divergence
- clustering
- branch emergence
- multimodality
- branch persistence
- reconvergence
- ensemble coherence

These features must be compared against simple spread-based baselines.

Complex ensemble geometry must earn its place through validation.

---

# 19. ENSEMBLE SPREAD

Ensemble spread is useful information but must not automatically be
interpreted as forecast error.

The system must explicitly test:

- spread versus eventual error
- spread growth versus eventual error
- spread acceleration versus eventual error
- low-spread/high-error cases
- high-spread/low-error cases

This prevents the system from blindly equating uncertainty with
failure.

---

# 20. FALSE CONFIDENCE

A particularly important failure cohort is:

LOW ENSEMBLE SPREAD
+
HIGH EVENTUAL ERROR

This may represent a false-confidence situation.

ForecastGuard should investigate whether its reliability model can detect
such cases better than conventional spread-based indicators.

This must be evaluated empirically.

---

# 21. MULTI-MODEL INTELLIGENCE

Where multiple forecast centres are available, compare:

- NCMRWF
- ECMWF
- NCEP
- UKMO
- JMA
- CMA
- other appropriate models

Availability will depend on the selected dataset and access.

Multi-model disagreement must not automatically be interpreted as
forecast failure.

The system should distinguish between:

### Broad predictability uncertainty

Many models disagree.

and:

### Model-relative divergence

NCMRWF behaves differently from peer models.

---

# 22. MODEL-RELATIVE FAILURE HYPOTHESIS

Investigate whether increasing NCMRWF divergence from peer forecasts
predicts NCMRWF-specific future error.

Conceptually:

D_t = distance(NCMRWF_t, peer_models_t)

and:

DeltaD_t = D_t - D_(t-1)

The distance metric must be scientifically appropriate to the forecast
field.

This is a hypothesis, not a guaranteed signal.

---

# 23. FORECAST TRAJECTORY ANALOGUES

Historical analogues should eventually consider more than atmospheric
state similarity.

Potential comparison levels:

1. Atmospheric state analogue
2. Current forecast analogue
3. Forecast trajectory analogue
4. Historical failure-pathway analogue

The system should determine whether trajectory-based retrieval actually
outperforms simpler analogues.

Do not report historical similarity statistics unless they are computed
from the stored historical dataset.

---

# 24. FAILURE PATHWAY MEMORY

The system may maintain a historical database containing:

- initial state
- forecast trajectory
- ensemble evolution
- model-relative evolution
- reliability trajectory
- verification
- failure fingerprint
- warning timing

The purpose is to answer:

> Have we previously observed a similar forecast-reliability pathway?

Similarity must be quantitatively defined and reproducible.

---

# 25. ATMOSPHERIC REGIME

Forecast reliability may depend on atmospheric regime.

Potential features include:

- 500 hPa geopotential
- MSLP
- winds
- vorticity
- divergence
- moisture convergence
- CAPE
- vertical shear
- temperature anomalies
- relevant circulation indices

Potential regime states may include:

- stable flow
- transition
- rapidly evolving flow

However, these categories must be validated rather than assumed.

---

# 26. REGIME TRANSITION

Investigate whether transition between atmospheric regimes is associated
with increasing forecast vulnerability.

The important question is not simply:

"What regime is this?"

but:

"Is the atmospheric state changing in a way associated with degraded
forecast reliability?"

---

# 27. OOD / NOVELTY

ForecastGuard may include an out-of-distribution or historical-density
component.

Its purpose is to identify states that lie outside the high-density
region of the historical reference distribution.

Preferred language:

"Low historical representation."

"State lies outside the high-density region of the reference
distribution."

Avoid unsupported language such as:

"This has never happened before."

"Unprecedented atmosphere."

OOD must NOT automatically imply forecast failure.

OOD should primarily affect:

- evidence quality
- model confidence
- uncertainty interpretation
- abstention behaviour

unless validation demonstrates otherwise.

---

# 28. ENSEMBLE-BASED FRAGILITY

The system may investigate a fragility proxy derived from existing
ensemble members.

Possible concept:

If initially similar ensemble members diverge substantially in
downstream forecast behaviour, the forecast may be considered
fragile.

This is an ensemble-based proxy.

Do NOT describe it as true counterfactual sensitivity.

The system cannot claim causal perturbation experiments merely from
ordinary ensemble members.

Fragility must be validated against subsequent forecast error.

If it adds no predictive value, remove it.

---

# 29. FAILURE HAZARD

ForecastGuard should investigate whether forecast failure can be
represented as a time-dependent hazard.

Conceptually:

H_t(tau) =
P(failure within tau | information available at time t)

The system should estimate when the probability of future failure
becomes operationally significant.

---

# 30. WARNING LEAD TIME

Define:

T_alert = first actionable alert time

T_failure = verified failure time

Warning lead:

L = T_failure - T_alert

The central operational objective is to maximize useful warning lead
while maintaining acceptable false-alarm and calibration behaviour.

An alert that occurs extremely early but is constantly wrong is not
considered successful.

---

# 31. EARLIEST TRUSTWORTHY WARNING

Do not optimize solely for earliest possible warning.

The desired warning should be:

EARLY
+
CALIBRATED
+
ACTIONABLE
+
STABLE

A useful system must balance warning lead against false alarms.

---

# 32. ALERT STABILITY

The system must evaluate:

- alert reversals
- alert duration
- false escalation
- persistent warnings
- risk-state oscillation

A system that repeatedly changes:

HIGH RISK
→ SAFE
→ HIGH RISK
→ SAFE

without meaningful improvement is operationally weak.

---

# 33. EVIDENCE QUALITY

ForecastGuard should distinguish:

### Strong evidence

Sufficient historical/model support.

### Moderate evidence

Useful but incomplete support.

### Limited evidence

Prediction is possible but uncertainty is substantial.

### Insufficient evidence

Available information does not justify a strong inference.

The model must be allowed to abstain.

---

# 34. SELECTIVE PREDICTION

Investigate whether the system performs better when it can explicitly
say:

"Insufficient evidence."

Evaluate whether abstention improves:

- calibration
- precision
- decision utility
- false-alarm behaviour

If abstention provides no meaningful benefit, do not retain unnecessary
complexity.

---

# 35. MODEL LADDER

ForecastGuard must use a model-development ladder.

### Model 0

Climatological baseline.

### Model 1

Simple statistical model.

Examples:

- logistic regression
- calibrated probability model

### Model 2

Structured tree model.

Examples:

- XGBoost
- LightGBM

### Model 3

Temporal trajectory model.

Only if justified.

Examples:

- TCN
- LSTM
- temporal transformer

### Model 4

Spatial representation model.

Only if spatial fields demonstrably improve performance.

Complexity must be justified by validation.

---

# 36. BASELINE REQUIREMENT

No advanced model may be considered successful unless compared
against appropriate simple baselines.

At minimum compare against:

- climatology
- persistence
- conventional uncertainty indicators
- simple statistical model
- tree-based ML model

A sophisticated model that cannot beat a simple baseline is not a
scientific improvement.

---

# 37. VALIDATION PRINCIPLE

All predictive experiments must use chronological validation.

Future information must never leak into training features.

Possible structure:

TRAIN

→ historical period

VALIDATION

→ later period

TEST

→ unseen later period

Exact periods depend on data availability.

---

# 38. NO DATA LEAKAGE

If predicting at lead D+5, only information available at that point
may be used.

Never use:

- later observations
- later forecast cycles
- future verification results
- future atmospheric states
- hindsight-derived features
- labels constructed using future information as predictor inputs

The label may depend on future observations because the purpose is to
predict future error.

The FEATURES may not.

---

# 39. HISTORICAL REPLAY REQUIREMENT

Historical replay must simulate the information timeline that would have
existed operationally.

For example:

Forecast issued

→ D+7 information available

→ D+6 information becomes available

→ D+5 information becomes available

→ ...

→ observations eventually arrive

→ verification occurs

The system must never allow future observations to influence an earlier
forecast-risk prediction.

---

# 40. CORE PERFORMANCE METRICS

Potential predictive metrics include:

- PR-AUC
- ROC-AUC
- Brier score
- calibration error
- reliability diagrams
- precision
- recall
- false-alarm rate
- warning lead time

The correct metric depends on the operational objective.

For rare bust events, PR-AUC should receive particular attention.

---

# 41. CALIBRATION

A probability must mean something.

If ForecastGuard outputs:

70% bust risk

then approximately 70% of comparable cases should eventually bust,
subject to the defined population and calibration method.

Calibration must be measured.

Do not equate high discrimination with reliable probability estimates.

---

# 42. REGIONAL VALIDATION

Performance should be evaluated across geographic regions.

Possible dimensions:

- North India
- Central India
- South India
- Northeast India
- West India
- coastal regions
- other scientifically meaningful regions

Exact regional definitions must be documented.

A model that performs well nationally but fails systematically in a
specific region must not be presented as uniformly reliable.

---

# 43. SEASONAL VALIDATION

Evaluate performance across relevant seasons.

For example:

- monsoon
- winter
- pre-monsoon
- post-monsoon

Performance should not be assumed to transfer equally across seasons.

---

# 44. LEAD-TIME VALIDATION

Evaluate:

D+1
D+2
...
D+10

Performance should be reported separately where appropriate.

The system must not hide poor long-range performance behind an aggregate
score.

---

# 45. EVENT-SPECIFIC VALIDATION

Where data permit, evaluate important event classes such as:

- heavy rainfall
- cyclones
- monsoon active/break conditions
- western disturbances
- heat-wave-related situations

Do not assume that one universal model is optimal for every phenomenon.

Compare universal and event/regime-conditioned approaches.

---

# 46. ABLATION TESTING

Every major advanced module must undergo ablation testing.

Example:

BASELINE

vs

BASELINE + trajectory

vs

BASELINE + ensemble dynamics

vs

BASELINE + multimodel

vs

BASELINE + historical memory

vs

BASELINE + regime/OOD

vs

FULL SYSTEM

The purpose is to determine which components actually contribute.

---

# 47. KILL-OR-KEEP RULE

Every advanced idea is experimental.

Remove a component if it:

- provides no meaningful predictive improvement
- only improves training performance
- damages calibration
- increases false alarms
- reduces operational stability
- cannot be reproduced
- cannot be scientifically explained
- adds complexity without decision value

Complexity must earn its place.

---

# 48. RESEARCH HYPOTHESES

Important hypotheses include:

### H1 — Path dependence

Forecast history contains information beyond the current forecast
state.

### H2 — Trajectory information

Forecast evolution improves failure prediction beyond simple
persistence/jumpiness indicators.

### H3 — Failure morphology

Forecast trajectory contains information about how a future failure
will occur.

### H4 — Early warning

ForecastGuard can detect degradation before verified forecast failure.

### H5 — False confidence

Some major forecast failures occur despite apparently low ensemble
uncertainty.

### H6 — Model-relative failure

NCMRWF-specific divergence from peer models may identify model-relative
failure.

### H7 — Failure memory

Historical forecast trajectories can provide useful analogues for
future failures.

### H8 — Evidence-aware prediction

Explicitly representing evidence quality and abstention can improve
reliability.

### H9 — Event-specific reliability

Forecast reliability behaviour differs by event/regime.

### H10 — Alert stability

A useful operational system requires stable warnings rather than only
high classification performance.

These are hypotheses.

They are NOT claims.

---

# 49. ADVANCED RESEARCH

Potential experimental research areas include:

- persistent homology
- topological data analysis
- mutual-information decay
- information-theoretic trajectory features
- causal discovery
- transfer entropy
- convergent cross mapping

These techniques must be treated as experiments.

They must first be compared with simple baselines.

If they do not provide meaningful additional value, remove them.

Do not include advanced mathematics merely to make the project appear
more sophisticated.

---

# 50. SCIENTIFIC LANGUAGE RULES

Never claim:

- perfect prediction
- certainty
- guaranteed warnings
- causality from correlation
- unprecedented atmospheric behaviour
- world-first novelty
- operational NCMRWF integration without authorization
- measured accuracy without measured evaluation
- historical evidence that was not actually computed

Prefer language such as:

"indicates elevated vulnerability"

"associated with increased risk"

"historically similar pathway"

"low historical representation"

"ensemble-based fragility proxy"

"model-relative divergence"

"evidence is limited"

"validation indicates"

when supported by actual results.

---

# 51. UNCERTAINTY OF FORECASTGUARD ITSELF

ForecastGuard predictions are themselves uncertain.

The system must distinguish:

### Forecast uncertainty

Uncertainty in the weather/NWP prediction.

from:

### ForecastGuard evidence confidence

Confidence that ForecastGuard has sufficient evidence to estimate
forecast reliability.

These are not the same thing.

---

# 52. DATA PROVENANCE

Every scientific result should be traceable to:

- dataset
- forecast cycle
- variable
- initialization time
- lead time
- observation period
- processing version
- model version
- feature version
- model version
- experiment configuration

Reproducibility is mandatory.

---

# 53. DATA QUALITY CONTROL

Every forecast dataset must pass checks for:

- file readability
- expected initialization time
- expected lead times
- expected members
- geographic coverage
- coordinates
- units
- accumulation semantics
- missing values
- duplicates

Every forecast-observation pair must pass:

- physical time-window compatibility
- grid compatibility
- unit compatibility
- missing-value checks
- land-mask consistency where relevant
- no future-information leakage

---

# 54. IMMUTABLE RAW DATA

Raw forecast and observation files should be preserved whenever
practical.

Processing should create derived datasets rather than silently
overwriting original data.

This allows later scientific auditing.

---

# 55. REPRODUCIBILITY

Every experiment must record:

- code version
- configuration
- data version
- random seed where relevant
- training period
- validation period
- test period
- features
- model parameters
- metrics

A result that cannot be reproduced should not be treated as a final
scientific result.

---

# 56. SCIENTIFIC OUTPUT HIERARCHY

ForecastGuard should ultimately produce:

## WHERE

Spatial reliability/bust-risk map.

## WHEN

Reliability trajectory and warning window.

## HOW

Failure fingerprint.

## WHY

Evidence and meteorological/model drivers.

## HAVE WE SEEN THIS PATHWAY?

Historical analogue/pathway memory.

## DID IT ACTUALLY WORK?

Verification and historical replay.

---

# 57. PRIMARY SCIENTIFIC OUTPUT

The ultimate operational output should be something like:

Forecast reliability:

[calibrated reliability assessment]

Bust risk:

[calibrated probability]

Lead-time:

[D+x]

Affected region:

[region]

Expected failure characteristics:

[failure fingerprint]

Primary evidence:

[evidence]

Evidence quality:

[quality]

Warning lead:

[validated lead time]

All values must be generated from actual backend data.

---

# 58. FINAL SCIENTIFIC PRINCIPLE

ForecastGuard is not successful because it contains many AI techniques.

It is successful only if evidence demonstrates that it can provide
earlier, better-calibrated, operationally useful information about
forecast vulnerability than appropriate simpler baselines.

Therefore:

## SIMPLE BASELINE FIRST.

## REAL DATA ALWAYS.

## NO LEAKAGE.

## VALIDATE EVERYTHING.

## COMPLEXITY MUST EARN ITS PLACE.

## NEVER FABRICATE SCIENTIFIC RESULTS.