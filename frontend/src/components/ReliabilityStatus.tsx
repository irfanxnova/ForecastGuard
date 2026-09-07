import React from "react";
import { DashboardState } from "../types/dashboard";

interface ReliabilityStatusProps {
  state: DashboardState;
  onInvestigateClick?: () => void;
  onToggleObservationReveal?: () => void;
  onSelectStorm?: (stormName: string) => void;
  onAssessReliability?: () => void;
}

export const ReliabilityStatus: React.FC<ReliabilityStatusProps> = ({
  state,
  onInvestigateClick,
  onToggleObservationReveal,
  onSelectStorm,
  onAssessReliability,
}) => {
  const { reliability, cycle } = state;

  // Calculate circular gauge stroke values (radius 38 -> circumference ~238.76)
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const isBustRiskKnown = typeof reliability.bustRiskPercent === "number" && reliability.bustRiskPercent !== null;
  const progressOffset = isBustRiskKnown
    ? circumference - (reliability.bustRiskPercent! / 100) * circumference
    : circumference;

  const isDegrading = reliability.state === "DEGRADING" || reliability.state === "VULNERABLE";
  const isHazardous = reliability.state === "HAZARDOUS" || reliability.state === "SEVERE";
  const isAwaiting = reliability.state === "AWAITING_VERIFIED_CASE";

  const stateClass = isHazardous
    ? "hazardous-glow"
    : isDegrading
    ? "degrading-glow"
    : isAwaiting
    ? "awaiting-glow"
    : "stable-glow";

  const stateLabel = isAwaiting ? "AWAITING OBSERVATION" : reliability.state;

  return (
    <section className="panel status-panel" aria-label="Forecast Reliability Status">
      {/* Operational Case Header Strip */}
      <div
        className="case-header-bar"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "7px 12px",
          background: "rgba(10, 17, 24, 0.75)",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          marginBottom: "10px",
          borderRadius: "4px",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "10.5px", fontWeight: 700, letterSpacing: "0.06em", color: "#F5B83D" }}>
            HISTORICAL CASE:
          </span>
          <select
            value={state.activeStormName || "MIDHILI"}
            onChange={(e) => onSelectStorm && onSelectStorm(e.target.value)}
            style={{
              background: "#0D141E",
              border: "1px solid rgba(245, 184, 61, 0.4)",
              color: "#FFFFFF",
              padding: "3px 8px",
              fontSize: "11px",
              borderRadius: "3px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <option value="MIDHILI">MIDHILI (Severe Bust: 548 km)</option>
            <option value="MICHAUNG">MICHAUNG (High Reliability: 44 km)</option>
            <option value="BIPARJOY">BIPARJOY (Recurvature: False Conf)</option>
            <option value="MOCHA">MOCHA (Init Displacement)</option>
            <option value="TEJ">TEJ (Rapid Intensification)</option>
            <option value="HAMOON">HAMOON (Recurvature Bust)</option>
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            className="demo-indicator-pill"
            style={{
              background: state.isDemoMode
                ? "rgba(245, 158, 11, 0.15)"
                : "rgba(69, 183, 209, 0.15)",
              color: state.isDemoMode ? "#F59E0B" : "#45B7D1",
              borderColor: state.isDemoMode ? "rgba(245, 158, 11, 0.3)" : "rgba(69, 183, 209, 0.3)",
              fontSize: "10px",
              padding: "2px 8px",
            }}
          >
            {state.isDemoMode
              ? "SCENARIO DEMO"
              : state.reliability.state === "AWAITING_VERIFIED_CASE"
              ? "LIVE INFERENCE"
              : "HISTORICAL REPLAY"}
          </span>
        </div>
      </div>

      {/* Panel Header */}
      <div className="status-panel-top">
        <div className="status-header-left">
          <div className={`alert-triangle-icon ${isAwaiting ? "icon-neutral" : ""}`}>
            <svg
              viewBox="0 0 24 24"
              width="20"
              height="20"
              fill="none"
              stroke={isAwaiting ? "#45B7D1" : isHazardous ? "#FF4D4D" : isDegrading ? "#F59E0B" : "#55D98A"}
              strokeWidth="2.2"
            >
              {isAwaiting ? (
                <>
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </>
              ) : (
                <>
                  <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </>
              )}
            </svg>
          </div>
          <h2 className="status-panel-title">FORECAST RELIABILITY STATUS</h2>
        </div>

        <div className="status-header-meta">
          <span className="meta-capsule">{cycle.model} {cycle.initTime}</span>
          <span className="meta-divider">|</span>
          <span className="meta-capsule highlight">Target Lead: {cycle.targetLead}</span>
          <span className="meta-window">{cycle.validWindow}</span>
        </div>
      </div>

      {/* Hero State + Circular Vulnerability Gauge */}
      <div className="status-hero-row">
        <div className="hero-text-block">
          <div className={`hero-state-label ${stateClass}`}>
            {stateLabel}
          </div>
          <div className="hero-subtitle">{reliability.subtitle}</div>
        </div>

        {/* Circular Gauge */}
        <div className="hero-gauge-wrapper">
          <div className="circular-gauge-container">
            <svg className="circular-gauge-svg" width="94" height="94" viewBox="0 0 94 94">
              {/* Background Track */}
              <circle
                cx="47"
                cy="47"
                r={radius}
                className="gauge-track"
                strokeWidth="8"
                fill="none"
              />
              {/* Progress Arc */}
              <circle
                cx="47"
                cy="47"
                r={radius}
                className={`gauge-progress ${isAwaiting ? "gauge-neutral" : ""}`}
                strokeWidth="8"
                fill="none"
                strokeDasharray={circumference}
                strokeDashoffset={progressOffset}
                strokeLinecap="round"
                transform="rotate(-90 47 47)"
              />
            </svg>
            <div className="gauge-content">
              <span className="gauge-value" style={{ fontSize: "19px" }}>
                {isBustRiskKnown ? `${reliability.bustRiskPercent}/100` : "--"}
              </span>
              <span className="gauge-label" style={{ fontSize: "8px", letterSpacing: "0.03em" }}>
                {isBustRiskKnown ? "VULNERABILITY" : "PENDING"}
              </span>
            </div>
          </div>

          <div className="gauge-delta-block">
            {reliability.deltaPercent !== null ? (
              <>
                <span className="delta-pill">
                  <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <line x1="12" y1="19" x2="12" y2="5" />
                    <polyline points="5 12 12 5 19 12" />
                  </svg>
                  +{reliability.deltaPercent}%
                </span>
                <span className="delta-meta">trajectory delta</span>
              </>
            ) : (
              <span className="delta-meta text-muted">Baseline nominal</span>
            )}
          </div>
        </div>
      </div>

      {/* Three Operational Metric Cards */}
      <div className="operational-metrics-row">
        {/* Metric 1: First Actionable Signal */}
        <div className="metric-card">
          <div className="metric-card-header">
            <div className="metric-icon-box amber-box">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#F5B83D" strokeWidth="2.2">
                <circle cx="12" cy="12" r="10" />
                <circle cx="12" cy="12" r="6" />
                <circle cx="12" cy="12" r="2" />
              </svg>
            </div>
            <span className="metric-title">FIRST ACTIONABLE SIGNAL</span>
          </div>
          <div className={`metric-value-large ${isAwaiting ? "highlight-muted" : "highlight-amber"}`}>
            {reliability.firstActionableSignal}
          </div>
          <div className="metric-caption">
            {reliability.firstActionableSignalDesc}
          </div>
        </div>

        {/* Metric 2: Expected Failure Window */}
        <div className="metric-card">
          <div className="metric-card-header">
            <div className="metric-icon-box danger-box">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#FF4D4D" strokeWidth="2.2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
            </div>
            <span className="metric-title">EXPECTED FAILURE WINDOW</span>
          </div>
          <div className={`metric-value-large ${isAwaiting ? "highlight-muted" : "highlight-danger"}`}>
            {reliability.expectedFailureWindow}
          </div>
          <div className="metric-caption">
            {reliability.expectedFailureWindowDesc}
          </div>
        </div>

        {/* Metric 3: Evidence Coverage */}
        <div className="metric-card">
          <div className="metric-card-header">
            <div className="metric-icon-box blue-box">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#45B7D1" strokeWidth="2.2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <polyline points="9 12 11 14 15 10" />
              </svg>
            </div>
            <span className="metric-title">EVIDENCE COVERAGE</span>
          </div>
          <div className={`metric-value-large ${isAwaiting ? "highlight-muted" : "highlight-blue"}`} style={{ fontSize: "14px", paddingTop: "4px" }}>
            {state.leadsData ? `${state.leadsData.length} verified fixes` : "8 verified fixes"}
          </div>
          <div className="metric-caption">
            101 verified leads · 13 cycles · 6 storms
          </div>
        </div>
      </div>

      {/* Key Message Callout */}
      <div className="key-message-card">
        <div className="message-icon">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#F5B83D" strokeWidth="2">
            <path d="M9 18h6" />
            <path d="M10 22h4" />
            <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14" />
          </svg>
        </div>

        <div className="message-body">
          <div className="message-header-row">
            <span className="message-label">OPERATIONAL INTERPRETATION</span>
          </div>
          <p className="message-text">{reliability.keyMessage}</p>
        </div>
      </div>

      {/* Action Buttons Row */}
      <div
        className="status-action-row"
        style={{
          display: "flex",
          gap: "8px",
          marginTop: "12px",
          flexWrap: "wrap",
        }}
      >
        <button
          className="investigate-btn"
          style={{
            flex: "1 1 140px",
            background: "linear-gradient(135deg, #F5B83D 0%, #D9981E 100%)",
            color: "#0A0E14",
            fontWeight: 700,
            justifyContent: "center",
          }}
          onClick={onAssessReliability || onInvestigateClick}
        >
          <span>ASSESS RELIABILITY</span>
        </button>

        <button
          className="investigate-btn"
          style={{
            flex: "1 1 140px",
            background: "rgba(245, 184, 61, 0.12)",
            border: "1px solid rgba(245, 184, 61, 0.4)",
            color: "#FFD36A",
            justifyContent: "center",
          }}
          onClick={onInvestigateClick}
        >
          <span>🔍 INVESTIGATE WHY</span>
        </button>

        {!state.isDemoMode && state.reliability.state !== "AWAITING_VERIFIED_CASE" && (
          <button
            className="investigate-btn"
            style={{
              flex: "1 1 170px",
              background: state.isObservationRevealed
                ? "rgba(239, 68, 68, 0.18)"
                : "rgba(69, 183, 209, 0.18)",
              border: `1px solid ${
                state.isObservationRevealed
                  ? "rgba(239, 68, 68, 0.45)"
                  : "rgba(69, 183, 209, 0.45)"
              }`,
              color: state.isObservationRevealed ? "#FF7878" : "#45B7D1",
              fontWeight: 600,
              justifyContent: "center",
            }}
            onClick={onToggleObservationReveal}
          >
            <span>
              {state.isObservationRevealed
                ? "🙈 HIDE OBSERVATION"
                : "👁 REVEAL OBSERVATION"}
            </span>
          </button>
        )}
      </div>
    </section>
  );
};
