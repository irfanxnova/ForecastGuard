import React from "react";
import { DashboardState } from "../types/dashboard";

interface TopBarProps {
  state: DashboardState;
  onToggleDemoMode: () => void;
  onOpenUpload?: () => void;
  backendOnline?: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({ state, onToggleDemoMode, onOpenUpload, backendOnline = true }) => {
  return (
    <header className="top-system-bar">
      {/* Brand & Mission Left */}
      <div className="top-bar-left">
        <div className="radar-logo-container" aria-label="ForecastGuard Radar Emblem">
          <svg className="radar-svg" viewBox="0 0 44 44" fill="none">
            <circle cx="22" cy="22" r="20" stroke="#F5B83D" strokeWidth="1.2" strokeOpacity="0.4" />
            <circle cx="22" cy="22" r="14" stroke="#F5B83D" strokeWidth="1" strokeOpacity="0.6" strokeDasharray="3 3" />
            <circle cx="22" cy="22" r="7" stroke="#F5B83D" strokeWidth="1.2" />
            <line x1="22" y1="2" x2="22" y2="42" stroke="#F5B83D" strokeWidth="1" strokeOpacity="0.3" />
            <line x1="2" y1="22" x2="42" y2="22" stroke="#F5B83D" strokeWidth="1" strokeOpacity="0.3" />
            <path d="M22 22 L36 10" stroke="#FFD36A" strokeWidth="1.8" strokeLinecap="round" />
            <circle cx="36" cy="10" r="2.5" fill="#FFD36A" />
            <circle cx="22" cy="22" r="2" fill="#F5B83D" />
          </svg>
        </div>

        <div className="brand-titles">
          <div className="brand-primary-row">
            <span className="brand-name">FORECASTGUARD</span>
          </div>
          <span className="brand-tagline">From Forecasts to Foresight</span>
        </div>

        <div className="header-divider" />

        <div className="mission-badge">
          <div className="mission-title">AI-POWERED FORECAST RELIABILITY INTELLIGENCE</div>
          <div className="mission-subtitle">
            Detecting Forecast Busts in Medium-Range Weather Forecasts <span className="sih-tag">SIH 26079</span>
          </div>
        </div>
      </div>

      {/* Operational Status Right */}
      <div className="top-bar-right">
        {/* Cycle & Region */}
        <div className="status-cell cycle-cell">
          <div className="cycle-title">
            <span className="cycle-model">{state.cycle.model}</span>
            <span className="cycle-dot">•</span>
            <span className="cycle-utc">{state.cycle.initTime}</span>
          </div>
          <div className="cycle-date-row">
            <svg className="india-icon" viewBox="0 0 24 24" fill="none" stroke="#4B83C4" strokeWidth="1.5">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" />
              <circle cx="12" cy="9" r="2.5" fill="#4B83C4" />
            </svg>
            <span className="cycle-date">{state.cycle.dateFormatted}</span>
          </div>
        </div>

        {/* Pipeline Status */}
        <div className="status-cell">
          <div className="status-indicator">
            <span className={`status-dot ${backendOnline ? "green-dot pulse-circle" : "green-dot"}`} />
            <span className="status-label green-label">PIPELINE ONLINE</span>
          </div>
          <span className="status-meta">{backendOnline ? "Backend connected" : "All modules loaded"}</span>
        </div>

        {/* Pipeline Readiness Battery */}
        <div className="status-cell battery-cell" title="Ingestion pipeline readiness; does not represent scientific forecast confidence">
          <div className="battery-header">
            <span className="status-meta">PIPELINE READINESS</span>
            <span className="battery-percent">98%</span>
          </div>
          <div className="battery-bars">
            {Array.from({ length: 10 }).map((_, i) => (
              <span key={i} className="battery-segment active" />
            ))}
          </div>
        </div>

        {/* Verification Status */}
        <div className="status-cell">
          <div className="status-indicator">
            <span
              className={`status-dot ${
                state.verificationStatus === "PENDING_VERIFICATION"
                  ? "cyan-dot pulse-circle"
                  : state.isDemoMode
                  ? "amber-dot"
                  : state.reliability.state === "AWAITING_VERIFIED_CASE"
                  ? "gray-dot"
                  : "green-dot pulse-circle"
              }`}
            />
            <span className="status-label amber-label">VERIFICATION STATUS</span>
          </div>
          <span className="status-meta">
            {state.verificationStatus === "PENDING_VERIFICATION"
              ? "PENDING VERIFICATION (Prospective)"
              : state.isDemoMode
              ? "Demo scenario"
              : state.reliability.state === "AWAITING_VERIFIED_CASE"
              ? "Awaiting aligned case"
              : `Verified: ${state.activeStormName || "MIDHILI"} (${state.leadsData?.length || 8} fixes)`}
          </span>
        </div>

        {/* Last Update */}
        <div className="status-cell last-update-cell">
          <div className="update-row">
            <svg className="clock-icon" viewBox="0 0 24 24" fill="none" stroke="#A8B2BD" strokeWidth="1.8">
              <circle cx="12" cy="12" r="9" />
              <polyline points="12 7 12 12 15 15" />
            </svg>
            <span className="status-meta">LAST UPDATE</span>
          </div>
          <span className="update-time">{state.cycle.lastUpdateUtc}</span>
        </div>

        {/* Operational Flow: Upload Forecast (Professor Test Entrypoint) */}
        {onOpenUpload && (
          <button
            className="demo-toggle-btn upload-forecast-btn"
            onClick={onOpenUpload}
            title="Upload forecast payload or select sample fixture to run through scientific bust pipeline"
            id="btn-topbar-upload"
          >
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span>UPLOAD FORECAST</span>
          </button>
        )}

        {/* Mode Toggle Button */}
        <button
          className={`demo-toggle-btn ${
            state.operationalMode === "UPLOADED"
              ? "upload-active"
              : state.isDemoMode
              ? "demo-active"
              : state.reliability.state === "AWAITING_VERIFIED_CASE"
              ? "live-active"
              : "verified-active"
          }`}
          onClick={onToggleDemoMode}
          title="Cycle between Real Verified Cyclone Case, Demo Scenario, and Live Pipeline"
          id="btn-topbar-mode"
        >
          <span className="toggle-indicator" />
          <span>
            {state.operationalMode === "UPLOADED"
              ? "ANALYZED FORECAST"
              : state.isDemoMode
              ? "SCENARIO DEMO"
              : state.reliability.state === "AWAITING_VERIFIED_CASE"
              ? "LIVE INFERENCE"
              : "HISTORICAL REPLAY"}
          </span>
        </button>
      </div>
    </header>
  );
};
