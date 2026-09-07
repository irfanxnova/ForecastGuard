import React from "react";
import { DashboardState } from "../../types/dashboard";

interface VerificationViewProps {
  state: DashboardState;
  onNavigateTab: (tab: string) => void;
}

export const VerificationView: React.FC<VerificationViewProps> = ({
  state: _state,
  onNavigateTab,
}) => {
  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            VERIFICATION METHODOLOGY & GROUND TRUTH PROTOCOL
          </h2>
          <span className="panel-subtitle">
            NCMRWF NEPS forecast center tracking vs official IMD/RSMC New Delhi Best Track
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

      {/* Methodology Architecture Pipeline */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px", marginBottom: "24px" }}>
        <div className="metric-card" style={{ padding: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#F5B83D", marginBottom: "6px" }}>
            01. EXACT-TIME MATCHING
          </div>
          <p style={{ fontSize: "11.5px", color: "#A8B2BD", lineHeight: 1.5 }}>
            Forecast valid times are strictly locked to 6-hourly synoptic verification timestamps (00, 06, 12, 18 UTC). No temporal interpolation or artificial step generation is permitted.
          </p>
        </div>

        <div className="metric-card" style={{ padding: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#45B7D1", marginBottom: "6px" }}>
            02. HAVERSINE TRACK ERROR
          </div>
          <p style={{ fontSize: "11.5px", color: "#A8B2BD", lineHeight: 1.5 }}>
            Continuous geodesic track displacement &Delta;(t) is computed between the MSLP-detected ensemble mean vortex center and the official IMD/RSMC Best Track position.
          </p>
        </div>

        <div className="metric-card" style={{ padding: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#FF7878", marginBottom: "6px" }}>
            03. DYNAMIC TOLERANCE &tau;(t)
          </div>
          <p style={{ fontSize: "11.5px", color: "#A8B2BD", lineHeight: 1.5 }}>
            Bust threshold scales with forecast lead: <strong>&tau; = 85.0 km</strong> for leads &le;24h, and <strong>&tau; = 120.0 km</strong> for leads &gt;24h, reflecting dynamical uncertainty growth.
          </p>
        </div>
      </div>

      {/* Verification Classification Criteria */}
      <div className="metric-card" style={{ padding: "16px", marginBottom: "20px" }}>
        <h3 style={{ fontSize: "13px", color: "#FFFFFF", marginBottom: "12px" }}>
          CLASSIFICATION & SEVERITY TAXONOMY
        </h3>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11.5px", textAlign: "left" }}>
            <thead>
              <tr style={{ background: "rgba(13, 20, 30, 0.9)", borderBottom: "1px solid rgba(255, 255, 255, 0.12)", color: "#8E9DAE" }}>
                <th style={{ padding: "8px 12px" }}>CATEGORY</th>
                <th style={{ padding: "8px 12px" }}>MATHEMATICAL CRITERIA</th>
                <th style={{ padding: "8px 12px" }}>OPERATIONAL DEFINITION</th>
                <th style={{ padding: "8px 12px" }}>VERIFIED ARCHIVE COUNT</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.05)" }}>
                <td style={{ padding: "8px 12px" }}>
                  <span className="badge badge-stable" style={{ fontSize: "10px" }}>NOMINAL</span>
                </td>
                <td style={{ padding: "8px 12px", fontFamily: "monospace", color: "#55D98A" }}>
                  &Delta;(t) &lt; &tau;(t)
                </td>
                <td style={{ padding: "8px 12px", color: "#C5D0DC" }}>
                  Forecast track error remains within operational tolerance envelope.
                </td>
                <td style={{ padding: "8px 12px", fontWeight: 700, color: "#FFFFFF" }}>77 leads (76.2%)</td>
              </tr>
              <tr style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.05)" }}>
                <td style={{ padding: "8px 12px" }}>
                  <span className="badge badge-degrading" style={{ fontSize: "10px" }}>DEGRADED</span>
                </td>
                <td style={{ padding: "8px 12px", fontFamily: "monospace", color: "#F5B83D" }}>
                  &tau;(t) &le; &Delta;(t) &lt; 1.5 &tau;(t)
                </td>
                <td style={{ padding: "8px 12px", color: "#C5D0DC" }}>
                  Tolerance exceeded; actionable divergence from observed trajectory.
                </td>
                <td style={{ padding: "8px 12px", fontWeight: 700, color: "#F5B83D" }}>14 leads (13.9%)</td>
              </tr>
              <tr>
                <td style={{ padding: "8px 12px" }}>
                  <span className="badge badge-hazardous" style={{ fontSize: "10px" }}>SEVERE BUST</span>
                </td>
                <td style={{ padding: "8px 12px", fontFamily: "monospace", color: "#EF4444" }}>
                  &Delta;(t) &ge; 1.5 &tau;(t)
                </td>
                <td style={{ padding: "8px 12px", color: "#C5D0DC" }}>
                  Severe failure; gross track displacement &gt;127.5 km (&le;24h) or &gt;180 km (&gt;24h).
                </td>
                <td style={{ padding: "8px 12px", fontWeight: 700, color: "#EF4444" }}>10 leads (9.9%)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
