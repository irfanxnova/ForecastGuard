import React from "react";
import { DashboardState } from "../types/dashboard";

interface DataEvidenceStatusProps {
  state: DashboardState;
}

export const DataEvidenceStatus: React.FC<DataEvidenceStatusProps> = ({ state }) => {
  const { dataStatus } = state;

  const renderStatusBadge = (status: "available" | "partial" | "pending") => {
    switch (status) {
      case "available":
        return (
          <span className="source-badge badge-avail">
            <span className="badge-symbol">✓</span> Available
          </span>
        );
      case "partial":
        return (
          <span className="source-badge badge-part">
            <span className="badge-symbol">◐</span> Partially Available
          </span>
        );
      case "pending":
        return (
          <span className="source-badge badge-pend">
            <span className="badge-symbol">⏱</span> Pending
          </span>
        );
    }
  };

  return (
    <section className="panel bottom-card-panel data-evidence-panel" aria-label="Data Ingestion and Pipeline Status">
      <div className="panel-header">
        <div className="panel-title-group">
          <h2 className="panel-title">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="#55D98A" strokeWidth="2">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
            DATA INGESTION & PIPELINE STATUS
          </h2>
          {state.isDemoMode && (
            <span className="demo-indicator-pill">DEMO SCENARIO</span>
          )}
        </div>
      </div>

      <div className="data-evidence-content">
        {/* Source Items List */}
        <div className="sources-list">
          {dataStatus.map((item) => (
            <div key={item.name} className="source-item-row">
              <div className="source-name-group">
                <span className={`source-dot dot-${item.status}`} />
                <span className="source-name">{item.name}</span>
              </div>
              <div className="source-status-col">
                {renderStatusBadge(item.status)}
              </div>
            </div>
          ))}
        </div>

        {/* Overall Availability Progress Bar */}
        <div className="overall-availability-box">
          <div className="overall-header-row">
            <span className="overall-label">Pipeline Ingestion Readiness</span>
            <span className="overall-percent">98%</span>
          </div>

          <div className="segmented-battery-large">
            {Array.from({ length: 18 }).map((_, i) => (
              <span
                key={i}
                className={`battery-cell ${i < 17 ? "filled" : "empty"}`}
              />
            ))}
          </div>
          <span className="battery-sub-note">Ingestion readiness; does not represent scientific forecast confidence.</span>
        </div>
      </div>
    </section>

  );
};
