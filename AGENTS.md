# ForecastGuard — Agent Constitution

## Project

ForecastGuard is an AI/ML-based forecast reliability intelligence system for SIH2026 Problem Statement SIH26079:

"AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts."

The system is intended primarily as an operational decision-support tool for meteorologists and professional forecast users.

ForecastGuard does not replace official forecasts or warnings.

Core product idea:

NWP tells us what may happen.
ForecastGuard tells us how much we should trust that forecast.

---

## NON-NEGOTIABLE RULES

1. Never fabricate weather data.

2. Never fabricate machine-learning predictions, accuracy, calibration,
   warning lead time, historical analogues, or scientific results.

3. Never hardcode a scientific risk score and present it as model output.

4. Never use future observations as predictor features.

5. Preserve chronological train/validation/test separation.

6. Every prediction must use only information that would have been
   available at the forecast lead being evaluated.

7. Never silently change scientific definitions, units, timestamps,
   accumulation windows, grids, or coordinate conventions.

8. Every data transformation must be traceable and reproducible.

9. Every ML experiment must be reproducible.

10. Prefer simple models before complex models.

11. No advanced feature or model is promoted unless validation shows
    that it adds measurable value over an appropriate baseline.

12. Never claim operational access to NCMRWF, IMD, TIGGE, or any other
    protected/authorized data source unless that access actually exists.

13. Never claim that simulated/demo data are real operational data.

14. Never invent historical cases or historical verification results.

15. UI values must ultimately come from the backend/data layer.
    Scientific values must never be permanently hardcoded into the UI.

16. Clearly distinguish demonstration data from real scientific data.

17. Never make unsupported causal claims from correlations.

18. Never describe OOD detection as proof that an event is unprecedented.

19. Never describe ensemble-based fragility as true counterfactual
    sensitivity unless scientifically justified.

20. If evidence is insufficient, the system may report:
    "Insufficient evidence."

---

## SCIENTIFIC PRINCIPLE

Forecast bust is treated as a dynamical process rather than only a
static binary outcome.

The system should investigate whether the trajectory toward forecast
failure can be detected earlier than conventional approaches.

Core operational question:

"How early can ForecastGuard reliably detect an upcoming forecast bust
at an acceptable false-alarm rate?"

---

## PRODUCT PRINCIPLE

The system has two levels:

### Operational layer
Simple, fast, decision-oriented.

The operator should quickly understand:

- WHERE reliability is deteriorating
- WHEN deterioration is expected
- HOW serious the risk is
- WHY the system is concerned
- WHETHER further investigation is warranted

### Investigation layer
Deep scientific evidence including:

- ensemble behaviour
- forecast trajectory
- multi-model comparison
- atmospheric state
- historical analogues
- regime information
- OOD/evidence quality
- verification
- forecast-vs-reality analysis

Design principle:

"Simple outside. Deep inside."

---

## UI VISUAL SOURCE OF TRUTH

The approved ForecastGuard dashboard reference image is the primary
visual source of truth for the application's visual language.

Future UI work must replicate or improve this visual identity.

Core visual characteristics:

- dark navy / charcoal foundation
- amber/gold ForecastGuard brand accent
- restrained semantic green/yellow/orange/red risk colours
- professional meteorological visualizations
- strong information hierarchy
- map-first operational experience
- reliability-focused presentation
- subtle glow/elevation
- compact but readable information density
- premium scientific/operational appearance

Do not introduce unrelated generic SaaS dashboard styling.

Do not create random visual styles for different pages.

Every screen must look like it belongs to the same ForecastGuard product.

---

## DEVELOPMENT PRINCIPLE

Do not attempt to build the entire project in one task.

Work in small, explicit, verifiable tasks.

Before substantial implementation:

1. Understand the requested task.
2. Inspect the existing project.
3. State the implementation plan.
4. Make the smallest appropriate changes.
5. Run relevant tests.
6. Inspect the result.
7. Report exactly what changed.
8. Report tests performed.
9. Report remaining issues.

Do not modify unrelated files.

Do not rewrite working systems unnecessarily.

---

## DATA PRINCIPLE

The eventual scientific system is intended to use real data such as:

- NCMRWF forecasts
- TIGGE forecasts where appropriate
- ensemble members
- IMD observations
- atmospheric state/reanalysis data
- historical forecast-error information

During UI development, simulated data may be used only when clearly
identified as demonstration data.

The data layer must be designed so demonstration data can later be
replaced by real backend data without redesigning the UI.

---

## ENGINEERING PRINCIPLE

Prefer:

- readable code
- modular architecture
- explicit types
- clear naming
- reproducible experiments
- automated tests
- documented interfaces
- version control
- small commits

Avoid:

- unnecessary dependencies
- giant monolithic files
- duplicated logic
- hidden magic numbers
- unexplained constants
- fake AI logic
- unnecessary complexity

---

## AI AGENT BEHAVIOUR

The coding agent must not assume that a feature is scientifically
valid simply because it is technically possible.

When scientific validity is uncertain:

1. identify the uncertainty,
2. do not silently invent an assumption,
3. ask for clarification if necessary,
4. otherwise implement the smallest defensible version.

When a complex method is proposed, compare it against a simpler baseline
before treating it as useful.

Complexity must earn its place.

---

## CURRENT DEVELOPMENT TARGET

Build ForecastGuard as a real scientific system as far as realistically
possible.

The SIH submission/demo should expose the strongest validated portion
of the system through a polished operational interface.

The demo must never be allowed to become disconnected from the actual
scientific architecture.

A polished interface is important.

Scientific correctness is more important.