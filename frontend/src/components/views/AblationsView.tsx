import React from "react";
import { DashboardState } from "../../types/dashboard";

interface AblationsViewProps {
  state: DashboardState;
  onNavigateTab: (tab: string) => void;
}

export const AblationsView: React.FC<AblationsViewProps> = ({
  onNavigateTab,
}) => {
  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            FEATURE ABLATIONS & M4 POST-MORTEM ANALYSIS
          </h2>
          <span className="panel-subtitle">
            Systematic evidence ladder demonstrating feature value and rationale for killing M4 cycle revision
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

      {/* M4 Post-Mortem Box */}
      <div
        className="metric-card"
        style={{
          padding: "16px",
          border: "1px solid rgba(239, 68, 68, 0.4)",
          background: "rgba(239, 68, 68, 0.04)",
          marginBottom: "20px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <h3 style={{ fontSize: "14px", color: "#FF7878", fontWeight: 800 }}>
            WHY M4 (CYCLE REVISION INSTABILITY) WAS KILLED
          </h3>
          <span className="badge badge-hazardous" style={{ fontSize: "10px" }}>KILLED IN RETROSPECTIVE AUDIT</span>
        </div>
        <p style={{ fontSize: "12px", color: "#E2E8F0", lineHeight: 1.55 }}>
          While consecutive forecast cycle revisions exhibit a moderate empirical association with verified track error (<strong>Pearson r = +0.4482</strong> across 41 prospective revision pairs), promotional validation revealed critical operational vulnerabilities:
        </p>
        <ul style={{ fontSize: "11.5px", color: "#C5D0DC", margin: "10px 0 0 16px", lineHeight: 1.5 }}>
          <li><strong>Overfitting on small sample:</strong> 41 revision pairs across 6 storms is statistically insufficient to train an autonomous revision penalty without risk of spurious correlations.</li>
          <li><strong>False confidence on stabilizing tracks:</strong> In cases where a revised cycle corrected an initial initialization error (e.g. MOCHA +06h), M4 incorrectly elevated bust probability even as the forecast track converged.</li>
          <li><strong>Agent Constitution Compliance:</strong> "No advanced feature or model is promoted unless validation shows that it adds measurable value over an appropriate baseline." M4 failed this test and was decisively decommissioned.</li>
        </ul>
      </div>

      {/* Feature Ablation Ladder */}
      <div className="metric-card" style={{ padding: "16px" }}>
        <h3 style={{ fontSize: "13px", color: "#FFFFFF", marginBottom: "12px" }}>
          M0 → M6 SCIENTIFIC ABLATION LADDER
        </h3>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11.5px", textAlign: "left" }}>
            <thead>
              <tr style={{ background: "rgba(13, 20, 30, 0.9)", borderBottom: "1px solid rgba(255, 255, 255, 0.12)", color: "#8E9DAE" }}>
                <th style={{ padding: "8px 10px" }}>STEP</th>
                <th style={{ padding: "8px 10px" }}>FEATURE FAMILY ADDED</th>
                <th style={{ padding: "8px 10px" }}>BRIER SCORE</th>
                <th style={{ padding: "8px 10px" }}>TEST MAE</th>
                <th style={{ padding: "8px 10px" }}>OUTCOME & DISPOSITION</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.05)" }}>
                <td style={{ padding: "8px 10px", fontWeight: 700 }}>M0</td>
                <td style={{ padding: "8px 10px", color: "#A8B2BD" }}>Zero NWP (Climatological Mean)</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>0.248</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>112.4 km</td>
                <td style={{ padding: "8px 10px", color: "#8E9DAE" }}>Reference baseline</td>
              </tr>
              <tr style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.05)", background: "rgba(85, 217, 138, 0.05)" }}>
                <td style={{ padding: "8px 10px", fontWeight: 700, color: "#55D98A" }}>M1</td>
                <td style={{ padding: "8px 10px", fontWeight: 700, color: "#FFFFFF" }}>+ Scalar Ensemble Spread</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace", color: "#55D98A" }}>0.182</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace", color: "#55D98A" }}>84.2 km</td>
                <td style={{ padding: "8px 10px", color: "#55D98A", fontWeight: 700 }}>PRIMARY MACHINE BASELINE</td>
              </tr>
              <tr style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.05)" }}>
                <td style={{ padding: "8px 10px", fontWeight: 700 }}>M2</td>
                <td style={{ padding: "8px 10px", color: "#FFFFFF" }}>+ Elliptical Spatial Anisotropy</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>0.178</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>82.6 km</td>
                <td style={{ padding: "8px 10px", color: "#45B7D1" }}>Provisional candidate</td>
              </tr>
              <tr style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.05)" }}>
                <td style={{ padding: "8px 10px", fontWeight: 700 }}>M3</td>
                <td style={{ padding: "8px 10px", color: "#FFFFFF" }}>+ Sarle's Bimodality & Translation Velocity</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>0.174</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>81.9 km</td>
                <td style={{ padding: "8px 10px", color: "#45B7D1" }}>Provisional candidate</td>
              </tr>
              <tr style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.05)", background: "rgba(239, 68, 68, 0.05)" }}>
                <td style={{ padding: "8px 10px", fontWeight: 700, color: "#EF4444" }}>M4</td>
                <td style={{ padding: "8px 10px", color: "#FF7878" }}>+ Cycle-to-Cycle Revision Jump</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace", color: "#EF4444" }}>0.216</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace", color: "#EF4444" }}>98.7 km</td>
                <td style={{ padding: "8px 10px", color: "#EF4444", fontWeight: 700 }}>KILLED (DECOMMISSIONED)</td>
              </tr>
              <tr style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.05)" }}>
                <td style={{ padding: "8px 10px", fontWeight: 700 }}>M5</td>
                <td style={{ padding: "8px 10px", color: "#FFFFFF" }}>+ Reliability Contradiction Index (RCI)</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>0.171</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>80.4 km</td>
                <td style={{ padding: "8px 10px", color: "#F5B83D" }}>Diagnostic overlay layer</td>
              </tr>
              <tr>
                <td style={{ padding: "8px 10px", fontWeight: 700 }}>M6</td>
                <td style={{ padding: "8px 10px", color: "#FFFFFF" }}>+ Integrated Candidate (M1+M2+M3+M5)</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>0.169</td>
                <td style={{ padding: "8px 10px", fontFamily: "monospace" }}>79.8 km</td>
                <td style={{ padding: "8px 10px", color: "#45B7D1" }}>Provisional research candidate</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
