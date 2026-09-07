import React, { useState, useEffect } from "react";
import { DashboardState } from "../../types/dashboard";
import { projectGeoToSvg, STORMS_CATALOG } from "../../data/casesData";
import southAsiaBorders from "../../data/south_asia_borders.json";

interface ForecastVsRealityViewProps {
  state: DashboardState;
  onSelectLead: (lead: string) => void;
  onSelectStorm?: (stormName: string) => void;
  onNavigateTab: (tab: string) => void;
}

export const ForecastVsRealityView: React.FC<ForecastVsRealityViewProps> = ({
  state,
  onSelectLead,
  onSelectStorm,
  onNavigateTab,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [revealedLeadsCount, setRevealedLeadsCount] = useState<number>(4); // default reveals up to +24h
  const leads = state.leadsData || [];
  const stormName = state.activeStormName || "MIDHILI";

  // Replay animation timer
  useEffect(() => {
    let timer: any = null;
    if (isPlaying) {
      timer = setInterval(() => {
        setRevealedLeadsCount((prev) => {
          if (prev >= leads.length) {
            setIsPlaying(false);
            return prev;
          }
          const nextCount = prev + 1;
          const currentLead = leads[nextCount - 1];
          if (currentLead) {
            onSelectLead(`+${String(currentLead.forecast_lead_hours).padStart(2, "0")}h`);
          }
          return nextCount;
        });
      }, 1400);
    }
    return () => clearInterval(timer);
  }, [isPlaying, leads, onSelectLead]);

  const handlePlayReplay = () => {
    setRevealedLeadsCount(1);
    setIsPlaying(true);
    if (leads[0]) {
      onSelectLead(`+${String(leads[0].forecast_lead_hours).padStart(2, "0")}h`);
    }
  };

  const handleRevealAll = () => {
    setIsPlaying(false);
    setRevealedLeadsCount(leads.length);
  };

  // Forecast and observed points
  const fPoints = leads.map((r) => {
    const pt = projectGeoToSvg(r.forecast_lat, r.forecast_lon);
    return { ...pt, lead: `+${String(r.forecast_lead_hours).padStart(2, "0")}h`, record: r };
  });

  const oPoints = leads.map((r) => {
    const pt = projectGeoToSvg(r.observed_lat, r.observed_lon);
    return { ...pt, lead: `+${String(r.forecast_lead_hours).padStart(2, "0")}h`, record: r };
  });

  const activeRecord = leads.find((r) => `+${String(r.forecast_lead_hours).padStart(2, "0")}h` === state.selectedLead) || leads[0];

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#45B7D1" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            FORECAST VS REALITY — OPERATIONAL GROUND TRUTH REPLAY
          </h2>
          <span className="panel-subtitle">
            Interactive side-by-side trajectory comparison: NCMRWF NEPS Track vs official IMD/RSMC Best Track
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

      {/* Case Selector and Replay Controller Toolbar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
          background: "rgba(10, 16, 24, 0.8)",
          padding: "10px 14px",
          borderRadius: "6px",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "11px", color: "#F5B83D", fontWeight: 700 }}>Cyclone Case:</span>
          <select
            value={stormName}
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

        {/* Play Controller Buttons */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <button
            className="investigate-btn"
            style={{
              background: isPlaying ? "rgba(239, 68, 68, 0.2)" : "linear-gradient(135deg, #F5B83D 0%, #D9981E 100%)",
              color: isPlaying ? "#FF7878" : "#0A0E14",
              border: isPlaying ? "1px solid rgba(239, 68, 68, 0.5)" : "none",
              padding: "5px 14px",
              fontSize: "11px",
              fontWeight: 700,
            }}
            onClick={isPlaying ? () => setIsPlaying(false) : handlePlayReplay}
          >
            <span>{isPlaying ? "⏸ PAUSE REPLAY" : "▶ PLAY REPLAY"}</span>
          </button>

          <button
            className="investigate-btn"
            style={{
              background: "rgba(69, 183, 209, 0.15)",
              color: "#45B7D1",
              border: "1px solid rgba(69, 183, 209, 0.35)",
              padding: "5px 14px",
              fontSize: "11px",
              fontWeight: 600,
            }}
            onClick={handleRevealAll}
          >
            <span>👁 REVEAL ALL ({leads.length} LEADS)</span>
          </button>
        </div>

        {/* Lead Timeline Tabs */}
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          {leads.map((r, i) => {
            const leadStr = `+${String(r.forecast_lead_hours).padStart(2, "0")}h`;
            const isRevealed = i < revealedLeadsCount;
            const isSelected = leadStr === state.selectedLead;
            return (
              <button
                key={r.forecast_lead_hours}
                style={{
                  background: isSelected
                    ? "#FFD36A"
                    : isRevealed
                    ? "rgba(245, 184, 61, 0.15)"
                    : "rgba(255, 255, 255, 0.04)",
                  color: isSelected ? "#0A0E14" : isRevealed ? "#FFFFFF" : "#71808C",
                  border: isSelected ? "1px solid #FFFFFF" : "1px solid rgba(255, 255, 255, 0.08)",
                  padding: "3px 6px",
                  fontSize: "10px",
                  borderRadius: "3px",
                  fontWeight: isSelected ? 800 : 500,
                  cursor: "pointer",
                }}
                onClick={() => {
                  setRevealedLeadsCount(Math.max(revealedLeadsCount, i + 1));
                  onSelectLead(leadStr);
                }}
              >
                {leadStr}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main SVG Replay Canvas */}
      <div style={{ background: "#070C12", border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: "6px", overflow: "hidden", marginBottom: "16px" }}>
        <svg viewBox="0 0 880 500" style={{ width: "100%", height: "auto", display: "block" }}>
          <rect width="880" height="500" fill="#070C12" />

          {/* Graticule */}
          <g stroke="rgba(180, 210, 235, 0.04)" strokeWidth="0.6" strokeDasharray="3 4">
            <line x1="80" y1="0" x2="80" y2="500" />
            <line x1="200" y1="0" x2="200" y2="500" />
            <line x1="320" y1="0" x2="320" y2="500" />
            <line x1="440" y1="0" x2="440" y2="500" />
            <line x1="560" y1="0" x2="560" y2="500" />
            <line x1="680" y1="0" x2="680" y2="500" />
            <line x1="800" y1="0" x2="800" y2="500" />
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

          {/* Full Forecast Track (Gold Line) */}
          <path
            d={fPoints.slice(0, revealedLeadsCount).reduce((acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${pt.x} ${pt.y}`, "")}
            fill="none"
            stroke="#F5B83D"
            strokeWidth="2.5"
            strokeLinecap="round"
          />

          {/* Observed RSMC Track (Cyan Line) */}
          <path
            d={oPoints.slice(0, revealedLeadsCount).reduce((acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${pt.x} ${pt.y}`, "")}
            fill="none"
            stroke="#45B7D1"
            strokeWidth="2.2"
            strokeDasharray="4 3"
            strokeLinecap="round"
          />

          {/* Error Vectors for Revealed Leads */}
          {fPoints.slice(0, revealedLeadsCount).map((fPt, idx) => {
            const oPt = oPoints[idx];
            if (!oPt) return null;
            return (
              <line
                key={`err-${idx}`}
                x1={fPt.x}
                y1={fPt.y}
                x2={oPt.x}
                y2={oPt.y}
                stroke="#EF4444"
                strokeWidth="1.4"
                strokeDasharray="2 2"
                opacity="0.85"
              />
            );
          })}

          {/* Forecast Fix Diamonds */}
          {fPoints.slice(0, revealedLeadsCount).map((pt) => {
            const isSelected = pt.lead === state.selectedLead;
            return (
              <g key={`f-pt-${pt.lead}`} style={{ cursor: "pointer" }} onClick={() => onSelectLead(pt.lead)}>
                <polygon
                  points={`${pt.x},${pt.y - 4.5} ${pt.x + 4.5},${pt.y} ${pt.x},${pt.y + 4.5} ${pt.x - 4.5},${pt.y}`}
                  fill={isSelected ? "#FFFFFF" : "#F5B83D"}
                />
                <text x={pt.x + 7} y={pt.y + 3} fill="#FFD36A" fontSize="8" fontWeight="700">
                  {pt.lead}
                </text>
              </g>
            );
          })}

          {/* Observed Fix Circles */}
          {oPoints.slice(0, revealedLeadsCount).map((pt) => (
            <g key={`o-pt-${pt.lead}`}>
              <circle cx={pt.x} cy={pt.y} r="3.5" fill="#45B7D1" />
              <circle cx={pt.x} cy={pt.y} r="6.5" stroke="#45B7D1" strokeWidth="0.8" fill="none" opacity="0.6" />
            </g>
          ))}

          {/* Active Lead Callout Badge */}
          {activeRecord && (
            <g transform="translate(600, 40)">
              <rect x="0" y="0" width="260" height="90" rx="6" fill="#0A0F15" fillOpacity="0.94" stroke="#F5B83D" strokeWidth="1" />
              <text x="14" y="22" fill="#FFD36A" fontSize="11" fontWeight="800">
                FIX DISPLACEMENT AT {state.selectedLead}
              </text>
              <text x="14" y="42" fill="#FFFFFF" fontSize="18" fontWeight="800">
                {activeRecord.track_error_km.toFixed(1)} km Error
              </text>
              <text x="14" y="60" fill="#A8B2BD" fontSize="9.5">
                Tolerance Threshold &tau;: {activeRecord.threshold_km.toFixed(1)} km
              </text>
              <text x="14" y="76" fill={activeRecord.bust_label === 1 ? "#EF4444" : "#55D98A"} fontSize="9.5" fontWeight="700">
                Verification State: {activeRecord.severity} {activeRecord.bust_label === 1 ? "(TOLERANCE BREACHED)" : "(NOMINAL)"}
              </text>
            </g>
          )}

          {/* Legend */}
          <g transform="translate(20, 440)">
            <rect x="0" y="0" width="310" height="42" rx="4" fill="#0A0F15" fillOpacity="0.9" stroke="rgba(255,255,255,0.12)" />
            <line x1="12" y1="14" x2="34" y2="14" stroke="#F5B83D" strokeWidth="2.5" />
            <polygon points="23,11 26,14 23,17 20,14" fill="#F5B83D" />
            <text x="40" y="17" fill="#F5B83D" fontSize="9" fontWeight="600">NCMRWF NEPS Track (Revealed: {revealedLeadsCount}/8)</text>
            <line x1="12" y1="28" x2="34" y2="28" stroke="#45B7D1" strokeWidth="2.0" strokeDasharray="4 2" />
            <circle cx="23" cy="28" r="2.5" fill="#45B7D1" />
            <text x="40" y="31" fill="#45B7D1" fontSize="9" fontWeight="600">Official IMD/RSMC Ground Truth</text>
          </g>
        </svg>
      </div>

      {/* Error Progression Bar Chart */}
      <div className="metric-card" style={{ padding: "16px" }}>
        <h3 style={{ fontSize: "13px", color: "#FFFFFF", marginBottom: "8px" }}>
          TRACK DISPLACEMENT EVOLUTION BY LEAD HOUR (+06h → +48h)
        </h3>
        <div style={{ height: "130px", display: "flex", alignItems: "flex-end", gap: "14px", padding: "10px 0" }}>
          {leads.map((r, i) => {
            const isRevealed = i < revealedLeadsCount;
            const leadStr = `+${String(r.forecast_lead_hours).padStart(2, "0")}h`;
            const isSelected = leadStr === state.selectedLead;
            const heightPercent = isRevealed ? Math.min(100, Math.round((r.track_error_km / 550) * 100)) : 0;
            const isSevere = r.severity === "SEVERE";

            return (
              <div
                key={r.forecast_lead_hours}
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  cursor: "pointer",
                  height: "100%",
                  justifyContent: "flex-end",
                }}
                onClick={() => {
                  setRevealedLeadsCount(Math.max(revealedLeadsCount, i + 1));
                  onSelectLead(leadStr);
                }}
              >
                {isRevealed && (
                  <span style={{ fontSize: "9px", color: isSevere ? "#EF4444" : "#FFFFFF", fontWeight: 700, marginBottom: "4px" }}>
                    {r.track_error_km.toFixed(0)} km
                  </span>
                )}
                <div
                  style={{
                    width: "70%",
                    height: `${Math.max(4, heightPercent)}%`,
                    background: !isRevealed
                      ? "rgba(255, 255, 255, 0.05)"
                      : isSevere
                      ? "linear-gradient(180deg, #FF4D4D 0%, #B91C1C 100%)"
                      : r.bust_label === 1
                      ? "#F5B83D"
                      : "#55D98A",
                    borderRadius: "3px 3px 0 0",
                    border: isSelected ? "1px solid #FFFFFF" : "none",
                  }}
                />
                <span style={{ fontSize: "10px", marginTop: "6px", color: isSelected ? "#FFD36A" : "#8E9DAE", fontWeight: isSelected ? 800 : 500 }}>
                  {leadStr}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
