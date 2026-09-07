import React from "react";
import { DashboardState } from "../types/dashboard";

interface HistoricalMatchesProps {
  state: DashboardState;
}

export const HistoricalMatches: React.FC<HistoricalMatchesProps> = ({ state }) => {
  const { historicalAnalogues } = state;

  return (
    <section className="panel bottom-card-panel historical-matches-panel" aria-label="Historical Trajectory Matches">
      <div className="panel-header">
        <div className="panel-title-group">
          <h2 className="panel-title">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="#8B7FD6" strokeWidth="2">
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
            </svg>
            HISTORICAL TRAJECTORY MATCHES
          </h2>
          <span className="panel-subtitle">Most similar past forecast trajectories</span>
          {state.isDemoMode && (
            <span className="demo-indicator-pill">DEMO SCENARIO</span>
          )}
        </div>

        <button className="view-all-link">
          <span>View All</span>
          <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>

      <div className="historical-list">
        {historicalAnalogues.length === 0 ? (
          <div className="empty-operational-analogues">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#8B7FD6" strokeWidth="1.5">
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
            </svg>
            <div className="empty-state-title">HISTORICAL MEMORY</div>
            <div className="empty-state-desc">Awaiting sufficient verified trajectory cases</div>
          </div>
        ) : (
          historicalAnalogues.map((item, index) => (
            <div key={item.id} className="historical-card-item">
              {/* Index Number */}
              <span className="hist-index">{index + 1}</span>

              {/* Thumbnail Canvas */}
              <div className="hist-thumbnail-box">
                <svg viewBox="0 0 48 36" width="48" height="36">
                  <rect width="48" height="36" fill="#0A1017" rx="3" />
                  {/* Simplified Subcontinent Outline */}
                  <path d="M 16 6 Q 26 8 32 14 L 28 26 Q 22 32 18 24 Z" fill="#131C26" stroke="#2D4660" strokeWidth="0.6" />
                  {/* Thermal Swirl Marker */}
                  <circle cx={20 + index * 4} cy={16 + (index % 2) * 4} r="7" fill="#F5B83D" fillOpacity="0.45" />
                  <circle cx={20 + index * 4} cy={16 + (index % 2) * 4} r="3" fill="#FF4D4D" fillOpacity="0.8" />
                </svg>
              </div>

              {/* Details Column */}
              <div className="hist-details">
                <div className="hist-row-top">
                  <span className="hist-date">{item.date}</span>
                  <span className="hist-similarity">Similarity: <strong>{item.similarity.toFixed(2)}</strong></span>
                </div>
                <div className="hist-outcome">
                  <span className="outcome-tag">Outcome:</span> {item.outcome}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

    </section>
  );
};
