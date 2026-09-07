import React from "react";
import { DashboardState } from "../types/dashboard";

interface ForecastVsObservedProps {
  state: DashboardState;
}

export const ForecastVsObserved: React.FC<ForecastVsObservedProps> = ({ state }) => {
  const isHistoricalReplay = !state.isDemoMode && state.reliability.state !== "AWAITING_VERIFIED_CASE";
  const isRevealed = state.isObservationRevealed;

  // Active lead record if available
  const activeRecord = state.leadsData?.find((r) => `+${String(r.forecast_lead_hours).padStart(2, "0")}h` === state.selectedLead);

  return (
    <section className="panel bottom-card-panel forecast-vs-observed-panel" aria-label="Forecast vs Observed Verification">
      <div className="panel-header">
        <div className="panel-title-group">
          <h2 className="panel-title">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="#45B7D1" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            {isHistoricalReplay ? "RETROSPECTIVE VERIFICATION" : "FORECAST vs OBSERVED"}{" "}
            <span className="title-annotation">
              {isHistoricalReplay
                ? isRevealed
                  ? "(Ground Truth Revealed)"
                  : "(Ground Truth Withheld)"
                : "(When available)"}
            </span>
          </h2>
          {isHistoricalReplay && (
            <span
              className="demo-indicator-pill"
              style={{
                background: isRevealed ? "rgba(239, 68, 68, 0.15)" : "rgba(69, 183, 209, 0.15)",
                color: isRevealed ? "#FF7878" : "#45B7D1",
                borderColor: isRevealed ? "rgba(239, 68, 68, 0.3)" : "rgba(69, 183, 209, 0.3)",
              }}
            >
              {isRevealed ? "REVEALED" : "REPLAY HIDDEN"}
            </span>
          )}
        </div>
      </div>

      <div className="forecast-vs-content">
        {/* Split Mini Previews */}
        <div className="split-previews-row">
          {/* NCMRWF Forecast Preview */}
          <div className="preview-card">
            <div className="preview-label">NCMRWF Forecast ({state.selectedLead})</div>
            <div className="preview-screen">
              <svg viewBox="0 0 90 55" width="90" height="55">
                <rect width="90" height="55" fill="#0A1118" rx="3" />
                <path d="M 30 10 Q 55 12 65 24 L 55 45 Q 40 50 35 35 Z" fill="#132030" stroke="#25384D" strokeWidth="0.6" />
                {/* Thermal Forecast Plume */}
                <ellipse cx="48" cy="28" rx="20" ry="14" fill="#F59E0B" fillOpacity="0.6" />
                <ellipse cx="50" cy="28" rx="10" ry="8" fill="#EF4444" fillOpacity="0.85" />
              </svg>
            </div>
          </div>

          {/* IMD Observed Preview */}
          <div className="preview-card">
            <div className="preview-label">
              {isHistoricalReplay
                ? isRevealed
                  ? "Official IMD/RSMC Fix"
                  : "IMD Ground Truth (Hidden)"
                : "IMD Observed (Pending)"}
            </div>
            <div className={`preview-screen ${isHistoricalReplay && isRevealed ? "" : "pending-screen"}`}>
              <svg viewBox="0 0 90 55" width="90" height="55">
                <rect width="90" height="55" fill="#0A1118" rx="3" />
                <path d="M 30 10 Q 55 12 65 24 L 55 45 Q 40 50 35 35 Z" fill="#132030" stroke="#25384D" strokeWidth="0.6" />
                {isHistoricalReplay && isRevealed ? (
                  <>
                    <circle cx="49" cy="29" r="6" fill="#55D98A" fillOpacity="0.4" stroke="#55D98A" strokeWidth="1.2" />
                    <circle cx="49" cy="29" r="2" fill="#55D98A" />
                  </>
                ) : (
                  <g stroke="rgba(180, 210, 235, 0.12)" strokeWidth="0.5">
                    <line x1="20" y1="0" x2="20" y2="55" />
                    <line x1="40" y1="0" x2="40" y2="55" />
                    <line x1="60" y1="0" x2="60" y2="55" />
                    <line x1="80" y1="0" x2="80" y2="55" />
                    <line x1="0" y1="18" x2="90" y2="18" />
                    <line x1="0" y1="36" x2="90" y2="36" />
                  </g>
                )}
              </svg>
            </div>
          </div>
        </div>

        {/* Operational Status Callout */}
        <div className="verification-status-banner">
          <div className="banner-icon">
            <svg
              viewBox="0 0 24 24"
              width="16"
              height="16"
              fill="none"
              stroke={isHistoricalReplay && isRevealed ? "#55D98A" : "#45B7D1"}
              strokeWidth="2"
            >
              {isHistoricalReplay && isRevealed ? (
                <>
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </>
              ) : (
                <>
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </>
              )}
            </svg>
          </div>
          <div className="banner-text-group">
            <div className="banner-meta">
              {isHistoricalReplay
                ? isRevealed
                  ? "Retrospective Verification"
                  : "Observation Withheld"
                : "Verification Status"}
            </div>
            <div
              className="banner-heading"
              style={{
                color: isHistoricalReplay && isRevealed ? "#55D98A" : isHistoricalReplay ? "#FFD36A" : "#ffffff",
              }}
            >
              {isHistoricalReplay
                ? isRevealed
                  ? activeRecord
                    ? `VERIFIED ERROR: ${activeRecord.track_error_km.toFixed(1)} km (Tau: ${activeRecord.threshold_km.toFixed(1)} km)`
                    : "VERIFIED GROUND TRUTH (RSMC NEW DELHI)"
                  : "OBSERVATION HIDDEN (REPLAY MODE)"
                : "LIVE OPERATIONAL INFERENCE"}
            </div>
            <div className="banner-caption">
              {isHistoricalReplay
                ? isRevealed
                  ? activeRecord
                    ? `Observed center at (${activeRecord.observed_lat.toFixed(2)}°N, ${activeRecord.observed_lon.toFixed(2)}°E). Verification classification: ${activeRecord.severity}.`
                    : "Post-event verification derived strictly from official IMD/RSMC Best Tracks 1982-2026 archive."
                  : "Future observation is hidden to prevent retrospective bias. Click [ REVEAL OBSERVATION ] to inspect IMD/RSMC ground truth."
                : "Prospective run: Future observations are strictly excluded from the inference path to prevent data leakage."}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
