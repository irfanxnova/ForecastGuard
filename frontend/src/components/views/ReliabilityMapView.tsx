import React, { useState } from "react";
import { DashboardState } from "../../types/dashboard";
import { STORMS_CATALOG, projectGeoToSvg } from "../../data/casesData";
import southAsiaBorders from "../../data/south_asia_borders.json";

interface ReliabilityMapViewProps {
  state: DashboardState;
  onSelectLead: (lead: string) => void;
  onSelectStorm?: (stormName: string) => void;
  onToggleObservationReveal?: () => void;
  onNavigateTab: (tab: string) => void;
}

export const ReliabilityMapView: React.FC<ReliabilityMapViewProps> = ({
  state,
  onSelectLead,
  onSelectStorm,
  onToggleObservationReveal,
  onNavigateTab,
}) => {
  const [showObservation, setShowObservation] = useState(state.isObservationRevealed);
  const [showAdminBorders, setShowAdminBorders] = useState(true);
  const [showSpreadEnvelope, setShowSpreadEnvelope] = useState(true);

  const handleToggleReveal = () => {
    setShowObservation(!showObservation);
    if (onToggleObservationReveal) {
      onToggleObservationReveal();
    }
  };

  const hasLeads = state.leadsData && state.leadsData.length > 0;
  const stormName = state.activeStormName || "MIDHILI";

  // Forecast points projection
  const fPoints = hasLeads
    ? state.leadsData!.map((r) => {
        const pt = projectGeoToSvg(r.forecast_lat, r.forecast_lon);
        return { ...pt, lead: `+${String(r.forecast_lead_hours).padStart(2, "0")}h`, record: r };
      })
    : [];

  // Observed points projection
  const oPoints = hasLeads
    ? state.leadsData!.map((r) => {
        const pt = projectGeoToSvg(r.observed_lat, r.observed_lon);
        return { ...pt, lead: `+${String(r.forecast_lead_hours).padStart(2, "0")}h`, record: r };
      })
    : [];

  const forecastPathD = fPoints.reduce((acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${pt.x} ${pt.y}`, "");
  const observedPathD = oPoints.reduce((acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${pt.x} ${pt.y}`, "");

  const activeLeadPoint = fPoints.find((p) => p.lead === state.selectedLead) || fPoints[0];
  const activeObsPoint = oPoints.find((p) => p.lead === state.selectedLead) || oPoints[0];

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Panel Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#F5B83D" strokeWidth="2">
              <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
              <line x1="8" y1="2" x2="8" y2="18" />
              <line x1="16" y1="6" x2="16" y2="22" />
            </svg>
            CYCLONE FORECAST TRACK RELIABILITY MAP
          </h2>
          <span className="panel-subtitle">
            Trajectory-specific forecast vulnerability for North Indian Ocean cyclone tracks (Not a nationwide pointwise bust model)
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

      {/* Map Controls Strip */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px", background: "rgba(10, 16, 24, 0.7)", padding: "10px 14px", borderRadius: "6px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "11px", color: "#F5B83D", fontWeight: 700 }}>Select Case:</span>
          <select
            value={state.activeStormName || "MIDHILI"}
            onChange={(e) => onSelectStorm && onSelectStorm(e.target.value)}
            className="select-control"
            style={{ padding: "4px 8px", fontSize: "11px", fontWeight: 600 }}
          >
            {STORMS_CATALOG.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name} ({s.highlightTag})
              </option>
            ))}
          </select>
        </div>

        {/* Lead Scrubber */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "11px", color: "#A8B2BD", fontWeight: 600 }}>Lead Scrubber:</span>
          {fPoints.map((pt) => (
            <button
              key={pt.lead}
              style={{
                background: pt.lead === state.selectedLead ? "#F5B83D" : "rgba(255, 255, 255, 0.08)",
                color: pt.lead === state.selectedLead ? "#0A0E14" : "#FFFFFF",
                border: "none",
                borderRadius: "3px",
                padding: "3px 7px",
                fontSize: "10.5px",
                fontWeight: pt.lead === state.selectedLead ? 700 : 500,
                cursor: "pointer",
              }}
              onClick={() => onSelectLead(pt.lead)}
            >
              {pt.lead}
            </button>
          ))}
        </div>

        {/* Layer Toggles & Reveal Button */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <label style={{ fontSize: "11px", color: "#A8B2BD", display: "flex", alignItems: "center", gap: "4px", cursor: "pointer" }}>
            <input type="checkbox" checked={showAdminBorders} onChange={(e) => setShowAdminBorders(e.target.checked)} />
            Borders
          </label>
          <label style={{ fontSize: "11px", color: "#A8B2BD", display: "flex", alignItems: "center", gap: "4px", cursor: "pointer" }}>
            <input type="checkbox" checked={showSpreadEnvelope} onChange={(e) => setShowSpreadEnvelope(e.target.checked)} />
            Spread
          </label>
          <button
            className="investigate-btn"
            style={{
              padding: "4px 10px",
              fontSize: "11px",
              background: showObservation ? "rgba(239, 68, 68, 0.2)" : "rgba(69, 183, 209, 0.2)",
              color: showObservation ? "#FF7878" : "#45B7D1",
              border: `1px solid ${showObservation ? "rgba(239, 68, 68, 0.4)" : "rgba(69, 183, 209, 0.4)"}`,
            }}
            onClick={handleToggleReveal}
          >
            {showObservation ? "🙈 Hide Observed Track" : "👁 Reveal Observed IMD Track"}
          </button>
        </div>
      </div>

      {/* SVG Canvas Container */}
      <div style={{ background: "#070C12", border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: "6px", overflow: "hidden", position: "relative" }}>
        <svg viewBox="0 0 880 540" style={{ width: "100%", height: "auto", display: "block" }}>
          <rect width="880" height="540" fill="#070C12" />

          {/* Graticule */}
          <g stroke="rgba(180, 210, 235, 0.04)" strokeWidth="0.6" strokeDasharray="3 4">
            <line x1="80" y1="0" x2="80" y2="540" />
            <line x1="200" y1="0" x2="200" y2="540" />
            <line x1="320" y1="0" x2="320" y2="540" />
            <line x1="440" y1="0" x2="440" y2="540" />
            <line x1="560" y1="0" x2="560" y2="540" />
            <line x1="680" y1="0" x2="680" y2="540" />
            <line x1="800" y1="0" x2="800" y2="540" />
            <line x1="0" y1="100" x2="880" y2="100" />
            <line x1="0" y1="200" x2="880" y2="200" />
            <line x1="0" y1="300" x2="880" y2="300" />
            <line x1="0" y1="400" x2="880" y2="400" />
          </g>

          {/* Landmass */}
          <g fill="#0C131B" stroke="rgba(120, 165, 195, 0.32)" strokeWidth="0.85">
            {Object.entries(southAsiaBorders as Record<string, string[]>).map(([country, paths]) => (
              <g key={country}>
                {paths.map((d, idx) => (
                  <path key={idx} d={d} />
                ))}
              </g>
            ))}
          </g>

          {/* Ocean Text */}
          <g fill="#3D5A75" fontSize="10" fontStyle="italic" fontWeight="500" letterSpacing="0.12em">
            <text x="220" y="380" textAnchor="middle">ARABIAN SEA</text>
            <text x="610" y="380" textAnchor="middle">BAY OF BENGAL</text>
          </g>

          {/* Spread Envelope */}
          {showSpreadEnvelope && fPoints.length > 2 && (
            <path
              d={`M ${fPoints[0].x - 14} ${fPoints[0].y + 12} ` +
                fPoints.map((p) => `L ${p.x - 18} ${p.y - 10}`).join(" ") + " " +
                fPoints.slice().reverse().map((p) => `L ${p.x + 18} ${p.y + 10}`).join(" ") + " Z"}
              fill="rgba(245, 184, 61, 0.08)"
              stroke="rgba(245, 184, 61, 0.2)"
              strokeWidth="1"
              strokeDasharray="3 3"
            />
          )}

          {/* Forecast Track */}
          <path d={forecastPathD} fill="none" stroke="#F5B83D" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

          {/* Forecast Nodes */}
          {fPoints.map((pt) => {
            const isSelected = pt.lead === state.selectedLead;
            return (
              <g key={`f-${pt.lead}`} style={{ cursor: "pointer" }} onClick={() => onSelectLead(pt.lead)}>
                <polygon
                  points={`${pt.x},${pt.y - 4.5} ${pt.x + 4.5},${pt.y} ${pt.x},${pt.y + 4.5} ${pt.x - 4.5},${pt.y}`}
                  fill={isSelected ? "#FFD36A" : "#F5B83D"}
                />
                {isSelected && <circle cx={pt.x} cy={pt.y} r="9" stroke="#FFD36A" strokeWidth="1.2" fill="none" opacity="0.8" />}
                <text x={pt.x + 8} y={pt.y + 3} fill="#F5B83D" fontSize="8" fontWeight="600">{pt.lead}</text>
              </g>
            );
          })}

          {/* Ground Truth RSMC Best Track (Conditional) */}
          {showObservation && (
            <g>
              {/* Error vectors */}
              {fPoints.map((fPt, idx) => {
                const oPt = oPoints[idx];
                if (!oPt) return null;
                return (
                  <line key={`vec-${idx}`} x1={fPt.x} y1={fPt.y} x2={oPt.x} y2={oPt.y} stroke="#EF4444" strokeWidth="1.2" strokeDasharray="2 2" opacity="0.8" />
                );
              })}

              <path d={observedPathD} fill="none" stroke="#45B7D1" strokeWidth="2.2" strokeDasharray="4 3" strokeLinecap="round" strokeLinejoin="round" />

              {oPoints.map((pt) => (
                <g key={`o-${pt.lead}`}>
                  <circle cx={pt.x} cy={pt.y} r="3.5" fill="#45B7D1" />
                  <circle cx={pt.x} cy={pt.y} r="6.5" stroke="#45B7D1" strokeWidth="0.8" fill="none" opacity="0.6" />
                </g>
              ))}

              {/* Error Callout at Active Lead */}
              {activeLeadPoint && activeObsPoint && (
                <g transform={`translate(${(activeLeadPoint.x + activeObsPoint.x) / 2}, ${(activeLeadPoint.y + activeObsPoint.y) / 2 - 14})`}>
                  <rect x="-55" y="-9" width="110" height="18" rx="3" fill="#0A0F15" fillOpacity="0.95" stroke="#EF4444" strokeWidth="1" />
                  <text x="0" y="3.5" fill="#FF6B6B" fontSize="9" fontWeight="700" textAnchor="middle">
                    {(activeLeadPoint as any).record?.track_error_km
                      ? `${(activeLeadPoint as any).record.track_error_km.toFixed(1)} km Error`
                      : "Verified Fix"}
                  </text>
                </g>
              )}
            </g>
          )}

          {/* Legend Overlay */}
          <g transform="translate(20, 480)">
            <rect x="0" y="0" width="280" height="46" rx="4" fill="#0A0F15" fillOpacity="0.9" stroke="rgba(255,255,255,0.12)" />
            <line x1="12" y1="15" x2="34" y2="15" stroke="#F5B83D" strokeWidth="2.5" />
            <polygon points="23,12 26,15 23,18 20,15" fill="#F5B83D" />
            <text x="40" y="18" fill="#F5B83D" fontSize="9" fontWeight="600">NCMRWF NEPS Track (+06h to +48h)</text>
            <line x1="12" y1="32" x2="34" y2="32" stroke="#45B7D1" strokeWidth="2.0" strokeDasharray="4 2" opacity={showObservation ? 1 : 0.4} />
            <circle cx="23" cy="32" r="2.5" fill="#45B7D1" opacity={showObservation ? 1 : 0.4} />
            <text x="40" y="35" fill={showObservation ? "#45B7D1" : "#71808C"} fontSize="9" fontWeight="600">
              {showObservation ? "Official IMD/RSMC Best Track" : "IMD Ground Truth (Revealed upon action)"}
            </text>
          </g>
        </svg>
      </div>

      {/* Synoptic Coordinate Table */}
      <div style={{ marginTop: "16px" }}>
        <h4 style={{ fontSize: "12px", color: "#FFFFFF", marginBottom: "8px" }}>
          SYNOPTIC TRACK COORDINATES & VERIFIED FIXES ({stormName})
        </h4>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "left" }}>
            <thead>
              <tr style={{ background: "rgba(13, 20, 30, 0.8)", borderBottom: "1px solid rgba(255, 255, 255, 0.1)", color: "#8E9DAE" }}>
                <th style={{ padding: "6px 10px" }}>LEAD</th>
                <th style={{ padding: "6px 10px" }}>VALID TIME</th>
                <th style={{ padding: "6px 10px" }}>FORECAST LAT/LON</th>
                <th style={{ padding: "6px 10px" }}>OBSERVED LAT/LON</th>
                <th style={{ padding: "6px 10px" }}>SPREAD</th>
                <th style={{ padding: "6px 10px" }}>TRACK ERROR</th>
                <th style={{ padding: "6px 10px" }}>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {state.leadsData?.map((r) => {
                const leadStr = `+${String(r.forecast_lead_hours).padStart(2, "0")}h`;
                const isSelected = leadStr === state.selectedLead;
                return (
                  <tr
                    key={r.forecast_lead_hours}
                    style={{
                      background: isSelected ? "rgba(245, 184, 61, 0.1)" : "transparent",
                      borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
                      cursor: "pointer",
                    }}
                    onClick={() => onSelectLead(leadStr)}
                  >
                    <td style={{ padding: "6px 10px", fontWeight: 700, color: isSelected ? "#F5B83D" : "#FFFFFF" }}>
                      {leadStr}
                    </td>
                    <td style={{ padding: "6px 10px", color: "#A8B2BD" }}>{r.forecast_valid_time.slice(11, 16)} UTC</td>
                    <td style={{ padding: "6px 10px", fontFamily: "monospace", color: "#FFD36A" }}>
                      {r.forecast_lat.toFixed(2)}°N, {r.forecast_lon.toFixed(2)}°E
                    </td>
                    <td style={{ padding: "6px 10px", fontFamily: "monospace", color: showObservation ? "#45B7D1" : "#71808C" }}>
                      {showObservation ? `${r.observed_lat.toFixed(2)}°N, ${r.observed_lon.toFixed(2)}°E` : "Withheld (Replay)"}
                    </td>
                    <td style={{ padding: "6px 10px", color: "#A8B2BD" }}>{r.ensemble_spread_km.toFixed(1)} km</td>
                    <td style={{ padding: "6px 10px", fontWeight: 700, color: showObservation ? (r.bust_label === 1 ? "#EF4444" : "#55D98A") : "#71808C" }}>
                      {showObservation ? `${r.track_error_km.toFixed(1)} km` : "--"}
                    </td>
                    <td style={{ padding: "6px 10px" }}>
                      {showObservation ? (
                        <span className={`badge ${r.bust_label === 1 ? "badge-hazardous" : "badge-stable"}`} style={{ fontSize: "9.5px", padding: "1px 5px" }}>
                          {r.severity}
                        </span>
                      ) : (
                        <span className="badge" style={{ background: "rgba(255,255,255,0.05)", color: "#8E9DAE", fontSize: "9.5px", padding: "1px 5px" }}>
                          WITHHELD
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
