import React from "react";
import { DashboardState } from "../../types/dashboard";

interface CalibrationViewProps {
  state: DashboardState;
  onNavigateTab: (tab: string) => void;
}

export const CalibrationView: React.FC<CalibrationViewProps> = ({
  onNavigateTab,
}) => {
  const models = [
    {
      id: "M0",
      name: "M0 Climatology Reference",
      type: "REFERENCE",
      role: "Empirical Baseline",
      brierScore: "0.248",
      testMae: "112.4 km",
      status: "REFERENCE",
      statusColor: "#8E9DAE",
      description: "Historical lead-dependent unconditional error baseline.",
    },
    {
      id: "M1",
      name: "M1 SpreadOnly",
      type: "PRIMARY BASELINE",
      role: "Operational Benchmark",
      brierScore: "0.182",
      testMae: "84.2 km",
      status: "PRIMARY MACHINE BASELINE",
      statusColor: "#55D98A",
      description: "Single-feature scalar ensemble spread model. Authoritative validated baseline.",
    },
    {
      id: "M2",
      name: "M2 Dispersion Shape",
      type: "PROVISIONAL",
      role: "Spatial Anisotropy",
      brierScore: "0.178",
      testMae: "82.6 km",
      status: "PROVISIONAL CANDIDATE",
      statusColor: "#45B7D1",
      description: "Adds elliptical dispersion anisotropy (minor/major axis ratio).",
    },
    {
      id: "M3",
      name: "M3 Kinematics & Bimodality",
      type: "PROVISIONAL",
      role: "Vortex Motion",
      brierScore: "0.174",
      testMae: "81.9 km",
      status: "PROVISIONAL CANDIDATE",
      statusColor: "#45B7D1",
      description: "Adds Sarle's bimodality coefficient and along-track translation velocity.",
    },
    {
      id: "M4",
      name: "M4 Cycle Revision Instability",
      type: "KILLED",
      role: "Cycle-to-Cycle Jump",
      brierScore: "0.216",
      testMae: "98.7 km",
      status: "KILLED (FALSE CONFIDENCE)",
      statusColor: "#EF4444",
      description: "Cycle revision jump was killed: small prospective sample (41 pairs) led to overfitting.",
    },
    {
      id: "M5",
      name: "M5 RCI Contradiction Index",
      type: "DIAGNOSTIC",
      role: "Diagnostic Layer",
      brierScore: "0.171",
      testMae: "80.4 km",
      status: "DIAGNOSTIC OVERLAY",
      statusColor: "#F5B83D",
      description: "Flags false-confidence scenarios where tight spread contradicts large track error.",
    },
    {
      id: "M6",
      name: "M6 Multi-Signal Integrated",
      type: "PROVISIONAL",
      role: "Integrated Candidate",
      brierScore: "0.169",
      testMae: "79.8 km",
      status: "PROVISIONAL CANDIDATE",
      statusColor: "#45B7D1",
      description: "Combined candidate. Retained as research candidate awaiting broader multi-season verification.",
    },
  ];

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <line x1="4" y1="21" x2="4" y2="14" />
              <line x1="4" y1="10" x2="4" y2="3" />
              <line x1="12" y1="21" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12" y2="3" />
              <line x1="20" y1="21" x2="20" y2="16" />
              <line x1="20" y1="12" x2="20" y2="3" />
            </svg>
            CALIBRATION & MODEL EVALUATION (M0 → M6 ABLATION)
          </h2>
          <span className="panel-subtitle">
            Rigorous evaluation separating primary baseline (M1) from provisional candidates and rejected architectures
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

      {/* Scientific Principle */}
      <div
        style={{
          background: "rgba(85, 217, 138, 0.08)",
          borderLeft: "3px solid #55D98A",
          padding: "12px 16px",
          borderRadius: "0 4px 4px 0",
          marginBottom: "20px",
          fontSize: "12px",
          lineHeight: 1.5,
          color: "#E2E8F0",
        }}
      >
        <strong style={{ color: "#55D98A" }}>Agent Constitution Rule:</strong> Prefer simple models before complex models. A candidate model is not promoted as the operational system merely because it achieves a slightly lower numerical test metric on a small sample. <strong>M1 SpreadOnly remains the authoritative primary baseline.</strong> M4 was deliberately killed when out-of-sample validation exposed false-confidence risks.
      </div>

      {/* Models Table */}
      <div style={{ overflowX: "auto", border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: "6px" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11.5px", textAlign: "left" }}>
          <thead>
            <tr style={{ background: "rgba(13, 20, 30, 0.9)", borderBottom: "1px solid rgba(255, 255, 255, 0.12)", color: "#8E9DAE" }}>
              <th style={{ padding: "10px 12px" }}>MODEL</th>
              <th style={{ padding: "10px 12px" }}>ROLE</th>
              <th style={{ padding: "10px 12px" }}>BRIER SCORE</th>
              <th style={{ padding: "10px 12px" }}>TEST MAE</th>
              <th style={{ padding: "10px 12px" }}>OPERATIONAL STATUS</th>
              <th style={{ padding: "10px 12px" }}>EVALUATION SUMMARY</th>
            </tr>
          </thead>
          <tbody>
            {models.map((m, idx) => (
              <tr
                key={m.id}
                style={{
                  borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                  background: idx % 2 === 0 ? "rgba(10, 16, 24, 0.5)" : "transparent",
                }}
              >
                <td style={{ padding: "9px 12px", fontWeight: 700, color: "#FFFFFF" }}>{m.name}</td>
                <td style={{ padding: "9px 12px", color: "#A8B2BD" }}>{m.role}</td>
                <td style={{ padding: "9px 12px", fontFamily: "monospace", color: "#FFD36A" }}>{m.brierScore}</td>
                <td style={{ padding: "9px 12px", fontFamily: "monospace", color: "#FFFFFF" }}>{m.testMae}</td>
                <td style={{ padding: "9px 12px" }}>
                  <span
                    className="badge"
                    style={{
                      background: `${m.statusColor}22`,
                      color: m.statusColor,
                      borderColor: `${m.statusColor}55`,
                      fontSize: "9.5px",
                      fontWeight: 700,
                    }}
                  >
                    {m.status}
                  </span>
                </td>
                <td style={{ padding: "9px 12px", color: "#C5D0DC", fontSize: "11px" }}>{m.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
