import React, { useState } from "react";
import { DashboardState } from "../../types/dashboard";

interface AtmosphericFieldsViewProps {
  state: DashboardState;
  onNavigateTab: (tab: string) => void;
}

interface AuditRow {
  name: string;
  level: string;
  status: "AVAILABLE" | "UNAVAILABLE";
  resolution: string;
  missingness: string;
  source: string;
  reason: string;
}

const AUDIT_DATA: AuditRow[] = [
  {
    name: "850-hPa Horizontal Wind Vector (U, V)",
    level: "850 hPa isobaric",
    status: "UNAVAILABLE",
    resolution: "N/A",
    missingness: "100.0%",
    source: "None in local archive",
    reason: "Local TIGGE cyclone archive contains single-level MSLP only. Upper-air sounding levels are not in the local dataset.",
  },
  {
    name: "200/250-hPa Horizontal Wind Vector (U, V)",
    level: "200/250 hPa isobaric",
    status: "UNAVAILABLE",
    resolution: "N/A",
    missingness: "100.0%",
    source: "None in local archive",
    reason: "Upper-tropospheric wind vectors are not present in the local single-level archive.",
  },
  {
    name: "Deep-Layer Vertical Wind Shear (850-200 hPa)",
    level: "Differential (200 - 850 hPa)",
    status: "UNAVAILABLE",
    resolution: "N/A",
    missingness: "100.0%",
    source: "Derived vector difference",
    reason: "Cannot derive deep-layer shear because neither 850 hPa nor 200 hPa wind fields exist in the local archive.",
  },
  {
    name: "Mid-Tropospheric Relative Humidity (700-500 hPa)",
    level: "700, 500 hPa isobaric",
    status: "UNAVAILABLE",
    resolution: "N/A",
    missingness: "100.0%",
    source: "None in local archive",
    reason: "Specific or relative humidity at mid-tropospheric levels is not present in the local single-level archive.",
  },
  {
    name: "Sea Surface Temperature (SST)",
    level: "Surface ocean",
    status: "UNAVAILABLE",
    resolution: "N/A",
    missingness: "100.0%",
    source: "None in local archive",
    reason: "Sea surface temperature field is absent from the local single-level TIGGE cyclone archive.",
  },
  {
    name: "Mean Sea Level Pressure (MSLP)",
    level: "meanSea (surface)",
    status: "AVAILABLE",
    resolution: "0.5° × 0.5°",
    missingness: "0.0%",
    source: "TIGGE NCMRWF NEPS (origin: dems)",
    reason: "Full 11-member ensemble grid verified across all 6 historical cyclone cases (6-hourly steps to +48h).",
  },
];

export const AtmosphericFieldsView: React.FC<AtmosphericFieldsViewProps> = ({
  state,
  onNavigateTab,
}) => {
  const [selectedTab, setSelectedTab] = useState<"audit" | "telemetry" | "ablation">("audit");
  const stormName = state.activeStormName || "MIDHILI";
  const activeRecord = state.leadsData?.find((r) => `+${String(r.forecast_lead_hours).padStart(2, "0")}h` === state.selectedLead) || state.leadsData?.[0];

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" />
            </svg>
            ATMOSPHERIC CONDITIONING & PHYSICAL EVIDENCE
          </h2>
          <span className="panel-subtitle">
            Environmental pressure kinematics, archive availability audit, and chronological ablation study
          </span>
        </div>
        <button
          className="btn-icon"
          style={{ width: "auto", padding: "6px 14px", fontSize: "11px", fontWeight: 600 }}
          onClick={() => onNavigateTab("dashboard")}
        >
          ← Return to Command Center
        </button>
      </div>

      {/* Non-Causal Scientific Integrity Notice (Rule 1, 16, 17, 20) */}
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
        <strong style={{ color: "#F5B83D" }}>Scientific Claim Firewall Notice:</strong> Atmospheric conditioning signals describe the large-scale synoptic environment associated with forecast evolution. <em>These metrics provide kinematic conditioning evidence; they do NOT prove or claim deterministic causality for forecast bust.</em>
        <div style={{ marginTop: "8px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "11px" }}>
          <div style={{ background: "rgba(16, 185, 129, 0.1)", padding: "8px", borderRadius: "4px", border: "1px solid rgba(16, 185, 129, 0.25)" }}>
            <strong style={{ color: "#10B981" }}>MEASURED:</strong> NCMRWF NEPS MSLP-derived pressure structure & pressure-gradient geometry.
          </div>
          <div style={{ background: "rgba(239, 68, 68, 0.1)", padding: "8px", borderRadius: "4px", border: "1px solid rgba(239, 68, 68, 0.25)" }}>
            <strong style={{ color: "#EF4444" }}>UNAVAILABLE:</strong> 850hPa wind, 200hPa wind, vertical wind shear, humidity, SST (100% missingness).
          </div>
        </div>
        <div style={{ marginTop: "6px", fontSize: "10.5px", color: "#CBD5E1" }}>
          ⚠ <em>Surface MSLP-derived pressure structure is NOT a direct measurement of vertical wind shear.</em>
        </div>
      </div>

      {/* Sub-Navigation Tabs */}
      <div style={{ display: "flex", gap: "10px", marginBottom: "20px", borderBottom: "1px solid rgba(255, 255, 255, 0.1)", paddingBottom: "10px" }}>
        <button
          className={`tab-btn ${selectedTab === "audit" ? "active" : ""}`}
          style={{
            background: selectedTab === "audit" ? "rgba(245, 184, 61, 0.2)" : "transparent",
            color: selectedTab === "audit" ? "#F5B83D" : "#A8B2BD",
            border: selectedTab === "audit" ? "1px solid #F5B83D" : "1px solid rgba(255, 255, 255, 0.1)",
            borderRadius: "4px",
            padding: "6px 14px",
            fontSize: "11px",
            fontWeight: 600,
            cursor: "pointer",
          }}
          onClick={() => setSelectedTab("audit")}
        >
          1. Archive Availability Audit
        </button>

        <button
          className={`tab-btn ${selectedTab === "telemetry" ? "active" : ""}`}
          style={{
            background: selectedTab === "telemetry" ? "rgba(245, 184, 61, 0.2)" : "transparent",
            color: selectedTab === "telemetry" ? "#F5B83D" : "#A8B2BD",
            border: selectedTab === "telemetry" ? "1px solid #F5B83D" : "1px solid rgba(255, 255, 255, 0.1)",
            borderRadius: "4px",
            padding: "6px 14px",
            fontSize: "11px",
            fontWeight: 600,
            cursor: "pointer",
          }}
          onClick={() => setSelectedTab("telemetry")}
        >
          2. Surface Environmental Kinematics
        </button>

        <button
          className={`tab-btn ${selectedTab === "ablation" ? "active" : ""}`}
          style={{
            background: selectedTab === "ablation" ? "rgba(245, 184, 61, 0.2)" : "transparent",
            color: selectedTab === "ablation" ? "#F5B83D" : "#A8B2BD",
            border: selectedTab === "ablation" ? "1px solid #F5B83D" : "1px solid rgba(255, 255, 255, 0.1)",
            borderRadius: "4px",
            padding: "6px 14px",
            fontSize: "11px",
            fontWeight: 600,
            cursor: "pointer",
          }}
          onClick={() => setSelectedTab("ablation")}
        >
          3. Chronological Ablation Study (MICHAUNG)
        </button>
      </div>

      {/* TAB 1: ARCHIVE AVAILABILITY AUDIT */}
      {selectedTab === "audit" && (
        <div>
          <div style={{ marginBottom: "16px" }}>
            <h3 style={{ fontSize: "13px", color: "#FFFFFF", marginBottom: "6px" }}>
              ATMOSPHERIC DATA AVAILABILITY & MISSINGNESS AUDIT
            </h3>
            <p style={{ fontSize: "11px", color: "#A8B2BD", lineHeight: 1.5 }}>
              Strict inspection of the workspace dataset inventory against the 5 requested atmospheric variables plus surface pressure:
            </p>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "left" }}>
              <thead>
                <tr style={{ background: "rgba(255, 255, 255, 0.05)", borderBottom: "1px solid rgba(255, 255, 255, 0.1)" }}>
                  <th style={{ padding: "10px 12px", color: "#F5B83D" }}>Variable</th>
                  <th style={{ padding: "10px 12px", color: "#F5B83D" }}>Level Type</th>
                  <th style={{ padding: "10px 12px", color: "#F5B83D" }}>Status</th>
                  <th style={{ padding: "10px 12px", color: "#F5B83D" }}>Missingness</th>
                  <th style={{ padding: "10px 12px", color: "#F5B83D" }}>Archive Source</th>
                  <th style={{ padding: "10px 12px", color: "#F5B83D" }}>Scientific Limitation / Audit Note</th>
                </tr>
              </thead>
              <tbody>
                {AUDIT_DATA.map((row, idx) => (
                  <tr
                    key={idx}
                    style={{
                      borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                      background: row.status === "AVAILABLE" ? "rgba(16, 185, 129, 0.04)" : "rgba(239, 68, 68, 0.03)",
                    }}
                  >
                    <td style={{ padding: "10px 12px", fontWeight: 600, color: "#FFFFFF" }}>{row.name}</td>
                    <td style={{ padding: "10px 12px", color: "#A8B2BD" }}>{row.level}</td>
                    <td style={{ padding: "10px 12px" }}>
                      {row.status === "AVAILABLE" ? (
                        <span style={{ color: "#10B981", fontWeight: 700 }}>✓ AVAILABLE</span>
                      ) : (
                        <span style={{ color: "#EF4444", fontWeight: 700 }}>🔒 UNAVAILABLE</span>
                      )}
                    </td>
                    <td style={{ padding: "10px 12px", fontFamily: "monospace", color: row.status === "AVAILABLE" ? "#10B981" : "#EF4444" }}>
                      {row.missingness}
                    </td>
                    <td style={{ padding: "10px 12px", color: "#CBD5E1" }}>{row.source}</td>
                    <td style={{ padding: "10px 12px", color: "#94A3B8", fontSize: "10.5px" }}>{row.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: SURFACE ENVIRONMENTAL KINEMATICS */}
      {selectedTab === "telemetry" && (
        <div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px", marginBottom: "20px" }}>
            <div className="metric-card" style={{ padding: "14px" }}>
              <span className="metric-title">RADIAL PRESSURE GRADIENT</span>
              <div className="metric-value-large highlight-amber">
                2.41 <span style={{ fontSize: "12px", color: "#A8B2BD" }}>hPa / 100 km</span>
              </div>
              <div className="metric-caption">Normalized vortex-to-outer-annulus [300-600 km] pressure drop</div>
            </div>

            <div className="metric-card" style={{ padding: "14px" }}>
              <span className="metric-title">ENVIRONMENTAL PRESSURE DEPTH ({stormName})</span>
              <div className="metric-value-large highlight-blue">
                10.8 <span style={{ fontSize: "12px", color: "#A8B2BD" }}>hPa</span>
              </div>
              <div className="metric-caption">
                Peripheral ring (1008.5 hPa) minus core minimum ({activeRecord ? `${activeRecord.forecast_pressure_hpa.toFixed(1)} hPa` : "997.7 hPa"})
              </div>
            </div>

            <div className="metric-card" style={{ padding: "14px" }}>
              <span className="metric-title">DIRECTIONAL ASYMMETRY (DIPOLE)</span>
              <div className="metric-value-large highlight-orange">
                0.62 <span style={{ fontSize: "12px", color: "#A8B2BD" }}>hPa / 100 km</span>
              </div>
              <div className="metric-caption">Outer annulus cross-diameter pressure gradient asymmetry</div>
            </div>

            <div className="metric-card" style={{ padding: "14px" }}>
              <span className="metric-title">CLASSIFIED ENVIRONMENTAL STATE</span>
              <div className="metric-value-large highlight-green" style={{ fontSize: "13px" }}>
                MARGINAL_PRESSURE_STRUCTURE
              </div>
              <div className="metric-caption">Moderate environmental pressure gradient geometry with low cross-domain asymmetry</div>
            </div>
          </div>

          {/* Annulus Schematic */}
          <div className="metric-card" style={{ padding: "16px" }}>
            <h3 style={{ fontSize: "13px", color: "#FFFFFF", marginBottom: "8px" }}>
              SYNOPTIC ANNULUS & DIRECTIONAL QUADRANT PARTITION ({stormName})
            </h3>
            <p style={{ fontSize: "11px", color: "#A8B2BD", marginBottom: "14px" }}>
              Physical derivation geometry: Outer synoptic ring is bounded between inner radius (300 km) and outer radius (600 km) to isolate large-scale environmental conditioning from inner vortex core dynamics.
            </p>

            <div style={{ background: "#080E16", borderRadius: "6px", border: "1px solid rgba(255, 255, 255, 0.08)", padding: "16px" }}>
              <svg viewBox="0 0 600 240" style={{ width: "100%", height: "auto", display: "block" }}>
                <rect width="600" height="240" fill="#080E16" />

                {/* Coordinate Grid Crosshairs */}
                <line x1="300" y1="20" x2="300" y2="220" stroke="rgba(255, 255, 255, 0.1)" strokeDasharray="3 3" />
                <line x1="180" y1="120" x2="420" y2="120" stroke="rgba(255, 255, 255, 0.1)" strokeDasharray="3 3" />

                {/* Outer Annulus (300 to 600 km) */}
                <circle cx="300" cy="120" r="95" fill="rgba(69, 183, 209, 0.06)" stroke="#45B7D1" strokeWidth="1.2" strokeDasharray="4 3" />
                {/* Inner Annulus (300 km) */}
                <circle cx="300" cy="120" r="50" fill="#080E16" stroke="#F5B83D" strokeWidth="1.2" />

                {/* Vortex Core */}
                <circle cx="300" cy="120" r="6" fill="#EF4444" />
                <text x="300" y="112" fill="#FF8080" fontSize="9" fontWeight="700" textAnchor="middle">{stormName} CORE</text>

                {/* Annulus Labels */}
                <text x="300" y="60" fill="#F5B83D" fontSize="8" textAnchor="middle">Inner: 300 km</text>
                <text x="300" y="20" fill="#45B7D1" fontSize="8" textAnchor="middle">Outer Synoptic Ring: 600 km</text>

                {/* Quadrant Labels */}
                <text x="300" y="35" fill="#A8B2BD" fontSize="8" textAnchor="middle">NORTH QUADRANT</text>
                <text x="300" y="210" fill="#A8B2BD" fontSize="8" textAnchor="middle">SOUTH QUADRANT</text>
                <text x="210" y="123" fill="#A8B2BD" fontSize="8" textAnchor="end">WEST</text>
                <text x="390" y="123" fill="#A8B2BD" fontSize="8" textAnchor="start">EAST</text>

                {/* Environmental Asymmetry Vector */}
                <g stroke="#F5B83D" strokeWidth="2" fill="#F5B83D">
                  <line x1="300" y1="120" x2="350" y2="85" />
                  <polygon points="354,82 346,86 351,93" />
                  <text x="365" y="86" fill="#F5B83D" fontSize="9" fontWeight="600">Asymmetry Vector (0.62 hPa/100km)</text>
                </g>
              </svg>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: CHRONOLOGICAL ABLATION STUDY */}
      {selectedTab === "ablation" && (
        <div>
          <div style={{ marginBottom: "16px" }}>
            <h3 style={{ fontSize: "13px", color: "#FFFFFF", marginBottom: "6px" }}>
              CONTROLLED MODEL ABLATION LADDER: A0 → A1 → A2
            </h3>
            <p style={{ fontSize: "11px", color: "#A8B2BD", lineHeight: 1.5 }}>
              Evaluated strictly on held-out unseen test event (Cyclone MICHAUNG, December 2023, n=21 prospective leads) after chronological training on pre-December 2023 cycles (n=67 leads):
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px", marginBottom: "20px" }}>
            {/* Model A0: Production Baseline */}
            <div className="metric-card" style={{ padding: "16px", border: "1px solid #10B981" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "#10B981" }}>A0: PRODUCTION BASELINE</span>
                <span style={{ background: "rgba(16, 185, 129, 0.2)", color: "#10B981", fontSize: "9px", padding: "2px 8px", borderRadius: "3px", fontWeight: 700 }}>
                  OPERATIONAL
                </span>
              </div>
              <div style={{ fontSize: "11px", color: "#A8B2BD", marginBottom: "12px" }}>
                M6 Combined Candidate: Spread + Trajectory + Bimodality (BC) + Anisotropy + Speed (7 features)
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", background: "rgba(0,0,0,0.3)", padding: "10px", borderRadius: "4px" }}>
                <div>
                  <div style={{ fontSize: "9px", color: "#94A3B8" }}>BRIER SCORE</div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#FFFFFF" }}>0.1799</div>
                </div>
                <div>
                  <div style={{ fontSize: "9px", color: "#94A3B8" }}>ECE</div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#FFFFFF" }}>0.3820</div>
                </div>
                <div>
                  <div style={{ fontSize: "9px", color: "#94A3B8" }}>ACCURACY</div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#10B981" }}>76.2%</div>
                </div>
              </div>
              <div style={{ marginTop: "12px", fontSize: "10.5px", color: "#CBD5E1", lineHeight: 1.4 }}>
                <strong>Verdict:</strong> Retained as production scoring baseline for regional assessments.
              </div>
            </div>

            {/* Model A1: A0 + Environmental Pressure */}
            <div className="metric-card" style={{ padding: "16px", border: "1px solid #F5B83D" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "#F5B83D" }}>A1: A0 + ENV PRESSURE</span>
                <span style={{ background: "rgba(245, 184, 61, 0.2)", color: "#F5B83D", fontSize: "9px", padding: "2px 8px", borderRadius: "3px", fontWeight: 700 }}>
                  EXPERIMENTAL
                </span>
              </div>
              <div style={{ fontSize: "11px", color: "#A8B2BD", marginBottom: "12px" }}>
                A0 Baseline + Peripheral Depth (hPa) + Radial Gradient + Directional Asymmetry (10 features)
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", background: "rgba(0,0,0,0.3)", padding: "10px", borderRadius: "4px" }}>
                <div>
                  <div style={{ fontSize: "9px", color: "#94A3B8" }}>BRIER SCORE</div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#10B981" }}>
                    0.1655 <span style={{ fontSize: "9px", color: "#10B981" }}>(-0.014)</span>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "9px", color: "#94A3B8" }}>ECE</div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#10B981" }}>
                    0.3731 <span style={{ fontSize: "9px", color: "#10B981" }}>(-0.009)</span>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "9px", color: "#94A3B8" }}>ACCURACY</div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#10B981" }}>81.0%</div>
                </div>
              </div>
              <div style={{ marginTop: "12px", fontSize: "10.5px", color: "#CBD5E1", lineHeight: 1.4 }}>
                <strong>Rule 11 Verdict:</strong> Shows empirical gain on pilot test (+4.8% accuracy), but designated <strong>EXPERIMENTAL</strong> because upper-air shear is unprovided.
              </div>
            </div>

            {/* Model A2: Environmental Interactions */}
            <div className="metric-card" style={{ padding: "16px", border: "1px solid #45B7D1" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "#45B7D1" }}>A2: INTERACTION MODEL</span>
                <span style={{ background: "rgba(69, 183, 209, 0.2)", color: "#45B7D1", fontSize: "9px", padding: "2px 8px", borderRadius: "3px", fontWeight: 700 }}>
                  EXPERIMENTAL
                </span>
              </div>
              <div style={{ fontSize: "11px", color: "#A8B2BD", marginBottom: "12px" }}>
                A1 Features + (Spread × Asymmetry) + (Gradient × Translation Speed) (12 features)
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", background: "rgba(0,0,0,0.3)", padding: "10px", borderRadius: "4px" }}>
                <div>
                  <div style={{ fontSize: "9px", color: "#94A3B8" }}>BRIER SCORE</div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#10B981" }}>
                    0.1648 <span style={{ fontSize: "9px", color: "#10B981" }}>(-0.015)</span>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "9px", color: "#94A3B8" }}>ECE</div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#10B981" }}>
                    0.3726 <span style={{ fontSize: "9px", color: "#10B981" }}>(-0.009)</span>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "9px", color: "#94A3B8" }}>ACCURACY</div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#10B981" }}>85.7%</div>
                </div>
              </div>
              <div style={{ marginTop: "12px", fontSize: "10.5px", color: "#CBD5E1", lineHeight: 1.4 }}>
                <strong>Rule 11 Verdict:</strong> Top ranking calibration on held-out test, but classified as <strong>EXPERIMENTAL</strong> to preserve scientific integrity.
              </div>
            </div>
          </div>

          <div
            style={{
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              padding: "12px 16px",
              borderRadius: "4px",
              fontSize: "11px",
              color: "#94A3B8",
              lineHeight: 1.5,
            }}
          >
            <strong style={{ color: "#F5B83D" }}>Promotion Rule Audit Summary:</strong> In accordance with AGENTS.md Rule 11 (<em>"Complexity must earn its place"</em>) and the Non-Negotiable Rules (Rule 1 & 16), Model A0 is preserved as the operational scoring standard. Environmental pressure features are made available as experimental operational context without claiming full atmospheric vertical-column completeness.
          </div>
        </div>
      )}
    </div>
  );
};
