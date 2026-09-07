import React from "react";
import { DashboardState, EvidenceFactor } from "../types/dashboard";

interface WhyReliabilityLowProps {
  state: DashboardState;
}

export const WhyReliabilityLow: React.FC<WhyReliabilityLowProps> = ({ state }) => {
  const { evidenceFactors } = state;

  const renderIcon = (icon: EvidenceFactor["icon"]) => {
    switch (icon) {
      case "divergence":
        return (
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#FF4D4D" strokeWidth="2">
            <path d="M2 12h4l3-8 4 16 3-8h6" />
          </svg>
        );
      case "drift":
        return (
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#FF4D4D" strokeWidth="2">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
            <polyline points="17 6 23 6 23 12" />
          </svg>
        );
      case "disagreement":
        return (
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#FF922B" strokeWidth="2">
            <circle cx="18" cy="5" r="3" />
            <circle cx="6" cy="12" r="3" />
            <circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
          </svg>
        );
      case "regime":
        return (
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#FF922B" strokeWidth="2">
            <ellipse cx="12" cy="5" rx="9" ry="3" />
            <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
          </svg>
        );
    }
  };

  return (
    <section className="panel why-low-panel" id="why-reliability-low" aria-label="Why Reliability Is Low">
      {/* Panel Header */}
      <div className="panel-header">
        <div className="panel-title-group">
          <h2 className="panel-title">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#F5B83D" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            WHY IS RELIABILITY LOW?
          </h2>
          <span className="panel-subtitle">Key contributing factors and evidence</span>
          {state.isDemoMode && (
            <span className="demo-indicator-pill">DEMO SCENARIO</span>
          )}
        </div>
      </div>

      {/* Factors List */}
      <div className="factors-list">
        {evidenceFactors.length === 0 ? (
          <div className="empty-operational-factors">
            <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#71808C" strokeWidth="1.5">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div className="empty-state-title">EVIDENCE FACTORS PENDING</div>
            <div className="empty-state-desc">
              Contributing evidence factors will rank automatically once the dynamical forecast trajectory is verified against observation data.
            </div>
          </div>
        ) : (
          evidenceFactors.map((factor) => (
            <div key={factor.id} className="factor-row">
              {/* Rank Number */}
              <div className="factor-rank">{factor.rank}</div>

              {/* Icon Container */}
              <div className={`factor-icon-box ${factor.level === "HIGH" ? "icon-danger" : "icon-amber"}`}>
                {renderIcon(factor.icon)}
              </div>

              {/* Text details */}
              <div className="factor-details">
                <div className="factor-title">{factor.title}</div>
                <div className="factor-desc">{factor.description}</div>
              </div>

              {/* Severity Pill */}
              <div className="factor-pill-wrapper">
                <span className={`badge ${factor.level === "HIGH" ? "badge-hazardous" : "badge-degrading"}`}>
                  {factor.level}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

    </section>
  );
};
