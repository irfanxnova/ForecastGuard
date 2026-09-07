import React from "react";
import { DashboardState } from "../../types/dashboard";
import { STORMS_CATALOG } from "../../data/casesData";

interface StatisticsViewProps {
  state: DashboardState;
  onNavigateTab: (tab: string) => void;
}

export const StatisticsView: React.FC<StatisticsViewProps> = ({
  onNavigateTab,
}) => {
  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <path d="M3 3v18h18" />
              <path d="m19 9-5 5-4-4-3 3" />
            </svg>
            AUDITED DATASET STATISTICS & EMPIRICAL METRICS
          </h2>
          <span className="panel-subtitle">
            Authoritative counts and correlation analyses from the deployment-verified cyclone track archive
          </span>
        </div>
        <button
          className="btn-icon"
          style={{ width: "auto", padding: "6px 12px", fontSize: "11px", fontWeight: 600 }}
          onClick={() => onNavigateTab("dashboard")}
        >
          ← Return to Command Center
        </button>
      </div>

      {/* Primary KPI Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px", marginBottom: "20px" }}>
        <div className="metric-card" style={{ padding: "14px" }}>
          <span className="metric-title">VERIFIED LEADS</span>
          <div className="metric-value-large highlight-blue">101</div>
          <div className="metric-caption">6-hourly exact-time fixes (+06h to +48h)</div>
        </div>

        <div className="metric-card" style={{ padding: "14px" }}>
          <span className="metric-title">FORECAST CYCLES</span>
          <div className="metric-value-large highlight-amber">13</div>
          <div className="metric-caption">00Z and 12Z NCMRWF NEPS runs</div>
        </div>

        <div className="metric-card" style={{ padding: "14px" }}>
          <span className="metric-title">VERIFIED STORMS</span>
          <div className="metric-value-large highlight-amber">6</div>
          <div className="metric-caption">Bay of Bengal & Arabian Sea (2023)</div>
        </div>

        <div className="metric-card" style={{ padding: "14px" }}>
          <span className="metric-title">VERIFIED FAILURES</span>
          <div className="metric-value-large highlight-danger">24</div>
          <div className="metric-caption">Contemporaneous tolerance breaches</div>
        </div>

        <div className="metric-card" style={{ padding: "14px" }}>
          <span className="metric-title">PROSPECTIVE ROWS</span>
          <div className="metric-value-large highlight-blue">88</div>
          <div className="metric-caption">Forecast rows with future lead targets</div>
        </div>

        <div className="metric-card" style={{ padding: "14px" }}>
          <span className="metric-title">PROSPECTIVE BUSTS</span>
          <div className="metric-value-large highlight-danger">37</div>
          <div className="metric-caption">Positive future failure windows</div>
        </div>

        <div className="metric-card" style={{ padding: "14px" }}>
          <span className="metric-title">REVISION PAIRS</span>
          <div className="metric-value-large highlight-muted">41</div>
          <div className="metric-caption">Cycle-to-cycle revision evaluations</div>
        </div>

        <div className="metric-card" style={{ padding: "14px" }}>
          <span className="metric-title">PEARSON ASSOCIATION</span>
          <div className="metric-value-large highlight-amber">+0.4482</div>
          <div className="metric-caption">Cycle revision / error correlation</div>
        </div>
      </div>

      {/* Association Callout */}
      <div
        style={{
          background: "rgba(245, 184, 61, 0.08)",
          borderLeft: "3px solid #F5B83D",
          padding: "12px 16px",
          borderRadius: "0 4px 4px 0",
          marginBottom: "20px",
          fontSize: "12px",
          lineHeight: 1.5,
          color: "#E2E8F0",
        }}
      >
        <strong style={{ color: "#FFD36A" }}>Statistical Interpretation:</strong> The revision/error correlation of <strong>r = +0.4482</strong> is an <em>empirical association</em>, NOT a causal relationship. It indicates that larger revisions between consecutive forecast cycles frequently coincide with larger eventual track displacements, but cycle jump does not cause track failure.
      </div>

      {/* Storm Summary Table */}
      <div className="metric-card" style={{ padding: "16px" }}>
        <h3 style={{ fontSize: "13px", color: "#FFFFFF", marginBottom: "12px" }}>
          VERIFIED DATASET BREAKDOWN BY CYCLONE
        </h3>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11.5px", textAlign: "left" }}>
            <thead>
              <tr style={{ background: "rgba(13, 20, 30, 0.9)", borderBottom: "1px solid rgba(255, 255, 255, 0.12)", color: "#8E9DAE" }}>
                <th style={{ padding: "8px 12px" }}>STORM</th>
                <th style={{ padding: "8px 12px" }}>BASIN</th>
                <th style={{ padding: "8px 12px" }}>CYCLES</th>
                <th style={{ padding: "8px 12px" }}>VERIFIED LEADS</th>
                <th style={{ padding: "8px 12px" }}>BUST FAILURES</th>
                <th style={{ padding: "8px 12px" }}>MEAN ERROR</th>
                <th style={{ padding: "8px 12px" }}>PEAK ERROR</th>
                <th style={{ padding: "8px 12px" }}>CHARACTERISTIC</th>
              </tr>
            </thead>
            <tbody>
              {STORMS_CATALOG.map((s, idx) => (
                <tr
                  key={s.name}
                  style={{
                    borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                    background: idx % 2 === 0 ? "rgba(10, 16, 24, 0.5)" : "transparent",
                  }}
                >
                  <td style={{ padding: "8px 12px", fontWeight: 700, color: "#FFFFFF" }}>{s.name}</td>
                  <td style={{ padding: "8px 12px", color: "#A8B2BD" }}>{s.basin}</td>
                  <td style={{ padding: "8px 12px", color: "#A8B2BD" }}>{s.cycles.length}</td>
                  <td style={{ padding: "8px 12px", fontWeight: 600, color: "#FFFFFF" }}>{s.verifiedLeadsCount}</td>
                  <td style={{ padding: "8px 12px", fontWeight: 700, color: s.bustsCount > 0 ? "#EF4444" : "#55D98A" }}>
                    {s.bustsCount}
                  </td>
                  <td style={{ padding: "8px 12px", color: "#FFD36A" }}>{s.meanErrorKm.toFixed(1)} km</td>
                  <td style={{ padding: "8px 12px", fontWeight: 700, color: s.maxErrorKm > 200 ? "#EF4444" : "#F59E0B" }}>
                    {s.maxErrorKm.toFixed(1)} km
                  </td>
                  <td style={{ padding: "8px 12px", color: "#C5D0DC" }}>{s.highlightTag}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
