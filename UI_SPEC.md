# ForecastGuard UI Specification

## 1. PRODUCT IDENTITY

Product name:

ForecastGuard

Tagline:

"Don't just see the forecast. See when its reliability changes."

Purpose:

ForecastGuard is an AI/ML-based forecast reliability intelligence
system for SIH2026 Problem Statement SIH26079.

It evaluates how vulnerable an existing medium-range NWP forecast is
to significant forecast failure and communicates that vulnerability
to professional operational users.

ForecastGuard is NOT:

- a public weather application
- a replacement for official forecasts
- a generic weather dashboard
- a generic AI analytics dashboard
- a new numerical weather prediction model

The primary UI audience is:

- meteorologists
- professional forecasters
- operational weather teams
- disaster-management and planning users
- scientific investigators

---

# 2. CORE UX PRINCIPLE

The interface must follow:

## "SIMPLE OUTSIDE. DEEP INSIDE."

The primary operational screen must be understandable within seconds.

The operator should immediately understand:

1. WHERE is forecast reliability deteriorating?
2. WHEN does reliability deteriorate?
3. HOW serious is the risk?
4. WHY is ForecastGuard concerned?
5. SHOULD I investigate further?

Advanced scientific information must be available through progressive
disclosure rather than being forced onto the first screen.

The application therefore has two conceptual layers:

### Operational Layer

Fast, simple, decision-oriented.

### Investigation Layer

Deep scientific analysis available when the user wants evidence.

Never sacrifice operational clarity merely to display more science.

---

# 3. VISUAL SOURCE OF TRUTH

The approved ForecastGuard dashboard reference image is the primary
visual source of truth.

All future screens, components, charts, cards, dialogs, maps,
navigation elements, alerts, and investigation views must visually
belong to the same product.

Do not create unrelated design languages for different pages.

If a new component is required and the reference image does not show
an exact example, extend the existing ForecastGuard design language
rather than inventing a completely new style.

The goal is consistency across the entire application.

---

# 4. VISUAL CHARACTER

ForecastGuard should feel like:

- professional
- scientific
- meteorological
- operational
- premium
- calm under pressure
- technically sophisticated
- information-dense but readable
- trustworthy
- modern without looking like a generic startup SaaS dashboard

It should NOT feel like:

- a consumer weather app
- a gaming interface
- a cyberpunk interface
- a cryptocurrency dashboard
- a generic enterprise admin panel
- a template-generated AI dashboard

The visual design must communicate scientific seriousness.

---

# 5. COLOR SYSTEM

Primary foundation:

Dark navy / charcoal / near-black.

The background should provide strong contrast while remaining
comfortable for prolonged operational use.

Primary brand accent:

Amber / golden yellow.

Amber represents the ForecastGuard identity and should be used for:

- brand elements
- active navigation
- important highlights
- selected controls
- key analytical emphasis
- subtle glow effects
- important non-severity UI elements

Do not flood the interface with amber.

Amber is the brand language, not the universal warning colour.

---

## Semantic risk colours

Use semantic colours consistently:

### STABLE

Green.

Meaning:

Forecast reliability is currently acceptable.

### WATCH

Yellow.

Meaning:

Early signs of degradation or elevated uncertainty.

### DEGRADING

Orange.

Meaning:

Reliability is deteriorating and deserves attention.

### HIGH RISK

Red/orange-red.

Meaning:

Substantial vulnerability to forecast failure.

### CRITICAL

Strong red.

Meaning:

Very high reliability concern requiring immediate investigation.

These semantic colours must never be used decoratively.

If a colour communicates risk, its meaning must remain consistent
throughout the entire application.

---

# 6. COLOR ACCESSIBILITY

Never communicate meaning through colour alone.

Every important risk state should also use at least one of:

- text label
- icon
- shape
- numerical value
- pattern
- position

Examples:

Do not show only a red dot.

Instead show:

RED DOT + HIGH RISK + numerical risk.

Charts and maps must remain interpretable for users with colour-vision
deficiencies.

Maintain strong text/background contrast.

---

# 7. TYPOGRAPHY

Typography must prioritize operational readability.

Use a modern clean sans-serif typeface.

Hierarchy:

### Level 1

Large, high-impact numerical values.

Examples:

Reliability

Bust Risk

Warning Lead

### Level 2

Section headings.

### Level 3

Card titles and labels.

### Level 4

Supporting descriptions and metadata.

Avoid unnecessarily tiny text.

Do not use decorative typography.

Numbers should be visually prominent when they represent operational
decisions.

---

# 8. INFORMATION HIERARCHY

The most important information must visually dominate.

Priority order on the primary screen:

1. Current reliability status
2. Bust risk
3. Vulnerable region
4. Lead-time window
5. Reliability trajectory
6. Why the system is concerned
7. Evidence quality
8. Detailed scientific modules

Do not give every metric equal visual weight.

A dashboard with everything highlighted is a dashboard where nothing
is highlighted.

---

# 9. PRIMARY APPLICATION LAYOUT

The main ForecastGuard application should use a professional
three-zone structure:

LEFT:

Persistent navigation sidebar.

CENTER:

Primary geographic and temporal intelligence.

RIGHT:

Current reliability assessment and explanation.

BOTTOM:

Scientific evidence and active alerts.

The central map should remain the visual anchor of the operational
screen.

---

# 10. LEFT NAVIGATION

The navigation sidebar should be dark, compact and professional.

Primary navigation should include concepts such as:

- Overview
- Alerts
- Cases
- Replay
- Verification
- Bust Atlas
- Data / System

Exact labels may evolve as the application grows, but the navigation
must remain simple.

The active page should be clearly identifiable using ForecastGuard's
amber accent.

Icons should be simple and consistent.

Do not overload the sidebar with dozens of menu items.

Advanced functions can be grouped under appropriate sections.

---

# 11. HEADER

The top header should provide operational context.

It may contain:

- ForecastGuard branding
- current forecast cycle
- UTC timestamp
- live/current status
- operational mode selector
- user/system status
- compact utility controls

The header should not become a navigation dumping ground.

Operational metadata should be visible without competing with the main
forecast reliability information.

---

# 12. MAIN MAP

The map is the primary geographic intelligence surface.

Core purpose:

## WHERE is forecast reliability vulnerable?

The map should support:

- India-focused visualization
- spatial reliability
- bust probability
- error-prone regions
- lead-time selection
- geographic interaction
- hover information
- selection of a region
- synchronized updates with other components

The map should visually emphasize meaningful spatial patterns.

Avoid unnecessary decorative map elements.

Do not make the map look like a consumer navigation application.

---

# 13. MAP INTERACTION

When the user changes forecast lead time:

D+1 → D+2 → ... → D+10

the map should update to the corresponding reliability state/data.

When the user selects a region:

the right-side reliability panel and relevant scientific evidence
should update accordingly.

The application should feel coordinated rather than like a collection
of independent widgets.

---

# 14. CURRENT FORECAST RELIABILITY PANEL

This is one of the most important components.

It should clearly communicate:

### Current reliability

A large, visually prominent reliability value.

### Reliability state

Examples:

STABLE

WATCH

DEGRADING

HIGH RISK

CRITICAL

### Bust probability

A clearly visible probability value when the model has sufficient
evidence.

### Change in reliability

Example:

"↓ 31 points since D+3"

Only display values that actually come from backend/model data.

Never hardcode scientific values into the production UI.

### Vulnerable region

Clearly identify the affected geographic area.

### Lead-time window

Clearly identify when risk is expected.

---

# 15. "WHY IS RELIABILITY LOW?"

This interaction is central to ForecastGuard.

The user should be able to immediately understand why the system is
concerned.

Potential evidence categories include:

- ensemble divergence
- ensemble spread evolution
- member clustering
- branch emergence
- multi-model disagreement
- model-relative divergence
- atmospheric regime transition
- historical trajectory similarity
- evidence/OOD status

Only display an evidence category when the backend actually provides
supporting information.

Never fabricate explanations.

Never generate decorative explanations disconnected from model output.

---

# 16. EVIDENCE QUALITY

ForecastGuard should communicate not only risk but also confidence in
the evidence supporting that risk.

Possible states:

- Strong evidence
- Moderate evidence
- Limited evidence
- Insufficient evidence

If the system does not have enough historical or model evidence, it
must be allowed to say:

## "Insufficient evidence."

Do not force an artificial probability when evidence quality is poor.

---

# 17. RELIABILITY TRAJECTORY

The D+1 through D+10 trajectory is a core product component.

Purpose:

## WHEN does forecast reliability change?

Display a chronological reliability progression.

The component should communicate:

- reliability level
- risk state
- direction of change
- onset of degradation
- possible warning window

Example visual concept:

D+1  D+2  D+3  D+4  D+5  D+6  D+7

STABLE → STABLE → WATCH → DEGRADING → HIGH RISK → HIGH RISK

The actual values and states must come from the backend.

Do not hardcode scientific results.

---

# 18. RELIABILITY CHANGE IS IMPORTANT

Do not focus only on the absolute risk.

The system should visually communicate meaningful changes.

Examples:

- risk increasing
- risk decreasing
- stable risk
- sudden escalation
- persistent degradation
- recovered reliability

This helps operational users understand forecast evolution.

---

# 19. ENSEMBLE OUTLOOK MODULE

The ensemble module should provide deeper evidence.

Potential visualizations:

- ensemble spread
- ensemble mean
- member distribution
- member clustering
- branching
- divergence
- scenario evolution

Avoid dumping dozens of unreadable spaghetti lines onto the user.

The operational view should summarize ensemble behaviour.

Detailed member-level analysis belongs in Investigator mode.

---

# 20. MULTI-MODEL MODULE

The system may compare NCMRWF against available peer models.

Potential information:

- model agreement
- model disagreement
- NCMRWF relative position
- temporal change in disagreement
- whether disagreement is broad or model-specific

The interface should distinguish:

### Broad predictability uncertainty

from

### NCMRWF-specific divergence

Do not imply that disagreement automatically means failure.

---

# 21. ATMOSPHERIC OVERVIEW

Provide a deeper scientific context panel.

Potential fields:

- geopotential
- pressure
- winds
- moisture
- vorticity
- divergence
- CAPE
- vertical shear
- relevant regime indicators

Only expose variables that are actually available and scientifically
used by the backend.

The UI should explain these through concise labels rather than
requiring the operator to decode technical jargon.

---

# 22. HISTORICAL MEMORY

ForecastGuard should be capable of displaying historical analogue
information when the backend supports it.

Potential presentation:

"Comparable historical forecast pathways"

Then show:

- number of comparable cases
- similarity information
- outcomes of comparable cases
- common failure patterns

Never invent historical counts or percentages.

Historical evidence must be traceable to real stored cases.

---

# 23. FORECAST VS REALITY

This is a core scientific verification feature.

The UI should eventually support:

FORECAST

versus

OBSERVATION

with synchronized:

- maps
- error fields
- timing
- intensity
- spatial displacement
- structural differences

This should help explain how a forecast actually failed.

---

# 24. FAILURE FINGERPRINT

When verification is available, summarize failure morphology.

Potential categories:

- Location error
- Timing error
- Intensity error
- Event miss
- False alarm
- Structural error

Do not reduce every failure to one RMSE number.

The fingerprint should communicate HOW the forecast failed.

---

# 25. HISTORICAL REPLAY / TIME MACHINE

Replay is a major demonstration and scientific-audit feature.

The user should be able to select a historical case and move through
forecast lead time.

Example:

D+1

↓

D+3

↓

D+5

↓

D+7

↓

Verification

At each point the interface must show only information that would have
been available at that historical forecast lead.

The replay must demonstrate that ForecastGuard did not use future
observations to make earlier predictions.

---

# 26. FAILURE PATHWAY

When sufficient evidence exists, show the progression toward failure.

Conceptual example:

STABLE

↓

ENSEMBLE DIVERGENCE

↓

MODEL DISAGREEMENT

↓

REGIME TRANSITION

↓

RELIABILITY DEGRADATION

↓

ALERT

↓

VERIFIED FAILURE

↓

AUTOPSY

This is a visualization of observed/model-supported evidence, not a
hardcoded causal chain.

Do not claim causality unless scientifically demonstrated.

---

# 27. ALERT CENTER

Alerts should be operationally useful.

Each alert should communicate:

- affected region
- lead time
- reliability state
- bust risk
- trend
- primary evidence
- timestamp
- status

Avoid notification spam.

Prioritize meaningful changes.

Alerts should be concise enough to scan rapidly.

---

# 28. INVESTIGATOR MODE

Investigator mode reveals deeper scientific information.

It may include:

- detailed ensemble behaviour
- ensemble geometry
- trajectory analysis
- model comparison
- atmospheric fields
- regime analysis
- OOD/evidence coverage
- historical analogues
- verification
- calibration
- model diagnostics

This mode may be significantly denser than the operational overview.

However, it must still use the same ForecastGuard visual language.

---

# 29. VERIFICATION PAGE

The verification interface should eventually support:

- forecast error
- bust severity
- calibration
- reliability
- warning lead time
- false alarm rate
- precision/recall
- PR-AUC
- ROC-AUC
- Brier score
- regional performance
- seasonal performance
- lead-time performance

Only display measured results.

Never create placeholder accuracy numbers that could be mistaken
for actual results.

If results are unavailable, clearly label the section as:

"Validation pending."

---

# 30. BUST ATLAS

The Bust Atlas is the historical memory of forecast failures.

It may contain:

- historical cases
- failure type
- region
- season
- lead time
- forecast trajectory
- ensemble evolution
- model disagreement
- reliability trajectory
- warning time
- verification
- autopsy

Users should be able to discover recurring failure pathways.

---

# 31. RESEARCH / EXPERIMENTAL FEATURES

Advanced features may include:

- forecast trajectory embeddings
- ensemble geometry
- OOD detection
- regime transitions
- forecast-pathway analogues
- fragility proxies
- information-theoretic signals
- topology-based features
- causal discovery experiments

These must never dominate the operational interface.

Experimental features must be visually or textually identified when
they are not yet validated.

---

# 32. SIH REQUIREMENT VISIBILITY

Every major SIH26079 requirement must have an obvious location.

The interface must clearly expose:

Forecast confidence

→ Reliability panel

Bust probability

→ Bust risk

D+1–D+10 reliability

→ Reliability trajectory

Error-prone regions

→ India risk map

Forecast uncertainty

→ Ensemble intelligence

Historical forecast-error behaviour

→ Historical Memory / Bust Atlas

Why confidence is low

→ Evidence / Why panel

AI-based detection

→ ForecastGuard ML engine

Spatial visualization

→ Interactive map

Forecast versus actual

→ Verification / Autopsy

System validation

→ Verification page

Operational usability

→ Overview / Alerts

API integration

→ Backend architecture

---

# 33. RESPONSIVE DESIGN

Desktop is the primary target because ForecastGuard is an operational
professional application.

However, layouts should degrade gracefully for smaller screens.

Do not simply shrink every component.

Prioritize:

1. reliability state
2. bust risk
3. affected region
4. trajectory
5. explanation

Secondary scientific panels may collapse or become scrollable.

---

# 34. ANIMATION

Animation should communicate change, not decorate the interface.

Appropriate uses:

- smooth lead-time transitions
- map updates
- risk-state changes
- panel expansion
- alert arrival
- trajectory progression
- replay timeline

Avoid:

- excessive bouncing
- unnecessary particle effects
- flashy transitions
- distracting continuous motion

Operational users must be able to focus.

---

# 35. GLOW AND DEPTH

Use subtle glow and elevation to establish hierarchy.

Amber glow may emphasize:

- active controls
- important brand elements
- selected state
- key analytical focus

Risk colours may glow subtly when an alert is active.

Never turn the whole interface into a neon/cyberpunk aesthetic.

The product should feel scientific, not theatrical.

---

# 36. CARDS

Cards should have:

- consistent radius
- consistent padding
- subtle borders
- controlled elevation
- clear hierarchy

Avoid excessive card nesting.

Do not put every individual value into its own giant card.

Related information should remain grouped.

---

# 37. CHARTS

Charts should prioritize interpretation.

Use charts to answer a specific question.

Examples:

"What is happening to reliability over lead time?"

"What is ensemble divergence doing?"

"How do models compare?"

"How well calibrated is the system?"

Avoid charts that exist only because they look impressive.

Charts must use the same ForecastGuard visual language.

---

# 38. DATA STATES

Every component must handle:

### Loading

Clearly communicate that data are being retrieved.

### Empty

Explain that no relevant data are available.

### Error

Explain what failed without exposing confusing technical details.

### Insufficient evidence

Clearly communicate that the system cannot make a sufficiently
supported inference.

### Demonstration data

Clearly identify simulated/demo content.

---

# 39. DEMO DATA RULE

During UI development, simulated data are allowed.

However:

- demo data must be centralized
- demo data must be clearly identifiable in development
- demo values must not be presented as real observations
- demo values must not be presented as measured ML performance
- demo historical cases must not be presented as real historical cases
  unless they actually are
- production scientific values must come from backend services

The frontend architecture must make replacement of demo data with real
backend data straightforward.

---

# 40. NO HARD-CODED SCIENCE

Never permanently hardcode:

- bust probability
- reliability score
- accuracy
- calibration
- historical case counts
- warning lead time
- model performance
- weather values
- observations

UI mock data may exist during development but must be isolated from
production data interfaces.

---

# 41. ACCESSIBILITY

The interface must support:

- keyboard navigation
- readable text
- strong contrast
- visible focus states
- semantic labels
- colour-independent risk communication
- usable tooltips
- screen-reader-friendly controls where practical

---

# 42. PERFORMANCE

The dashboard should remain responsive while displaying:

- geographic data
- forecast fields
- ensemble information
- charts
- historical cases

Prefer efficient rendering.

Do not load enormous scientific datasets into the browser when only
aggregated information is needed.

Use backend processing for expensive scientific operations.

---

# 43. COMPONENT CONSISTENCY

Reusable components should be created for:

- risk badges
- reliability cards
- evidence items
- alert cards
- chart containers
- map overlays
- trajectory indicators
- modal/dialog patterns
- tabs
- selectors
- metric displays

Do not duplicate slightly different versions of the same component.

---

# 44. VISUAL QUALITY STANDARD

Before considering a screen finished, compare it against the approved
ForecastGuard reference image.

Check:

- spacing
- alignment
- typography
- contrast
- colour usage
- hierarchy
- card proportions
- map dominance
- density
- navigation
- risk semantics
- consistency

The application should look like a single professionally designed
product.

---

# 45. JUDGE-FIRST PRINCIPLE

A judge should understand the product quickly.

The first screen should communicate:

FORECASTGUARD

Forecast reliability intelligence.

Current reliability.

Bust risk.

Affected region.

Lead-time window.

Reliability trajectory.

Why the system is concerned.

The advanced science should become visible when the judge asks:

"Why?"

This creates a natural demonstration progression:

1. See the problem.
2. See the risk.
3. See where it occurs.
4. See when reliability deteriorates.
5. Ask why.
6. Inspect evidence.
7. Replay a historical case.
8. Compare forecast with reality.
9. Inspect validation.

---

# 46. FINAL DESIGN PRINCIPLE

ForecastGuard should never look like a collection of AI-generated
screens.

It must feel like one coherent scientific instrument.

The interface should communicate:

WHERE → Map

WHEN → Reliability trajectory

HOW → Failure fingerprint

WHY → Evidence

HAVE WE SEEN THIS PATHWAY? → Historical memory

DID IT ACTUALLY WORK? → Verification / Replay

The operational experience must remain simple.

The scientific depth must remain available.

## SIMPLE OUTSIDE.

## DEEP INSIDE.

## FORECASTGUARD.