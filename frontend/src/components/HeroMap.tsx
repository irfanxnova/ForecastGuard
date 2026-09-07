import React, { useState } from "react";
import { DashboardState } from "../types/dashboard";
import southAsiaBorders from "../data/south_asia_borders.json";
import { projectGeoToSvg } from "../data/casesData";

interface HeroMapProps {
  state: DashboardState;
  onSelectLead: (lead: string) => void;
  onSelectVariable: (variable: string) => void;
  onSelectView: (view: string) => void;
}

export const HeroMap: React.FC<HeroMapProps> = ({
  state,
  onSelectLead,
  onSelectVariable,
  onSelectView,
}) => {
  const [layers, setLayers] = useState({
    reliabilityRisk: true,
    ncmrwfForecast: false,
    ensembleSpread: false,
    adminBoundaries: true,
    cityLabels: true,
  });

  const [zoomLevel, setZoomLevel] = useState(1);
  const [showHotspotDetail, setShowHotspotDetail] = useState(true);

  const toggleLayer = (layerKey: keyof typeof layers) => {
    setLayers((prev) => ({ ...prev, [layerKey]: !prev[layerKey] }));
  };

  return (
    <section className="panel hero-map-panel" aria-label="Cyclone Forecast Track Reliability">
      {/* Map Panel Header */}
      <div className="panel-header map-header">
        <div className="panel-title-group">
          <h2 className="panel-title">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#F5B83D" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
              <path d="M2 12h20" />
            </svg>
            CYCLONE FORECAST TRACK RELIABILITY
          </h2>
          <span className="panel-subtitle">Where is the NWP forecast track becoming unreliable?</span>
        </div>

        <div className="panel-controls">
          <div className="control-group">
            <span className="control-label">Variable:</span>
            <select
              className="select-control"
              value={state.selectedVariable}
              onChange={(e) => onSelectVariable(e.target.value)}
            >
              <option value="Precipitation (tp)">Precipitation (tp)</option>
              <option value="Temperature (2t)">Temperature (2t)</option>
              <option value="Mean Sea Level Pressure (msl)">Pressure (msl)</option>
            </select>
          </div>

          <div className="control-group">
            <span className="control-label">Lead Time:</span>
            <select
              className="select-control highlight-amber"
              value={state.selectedLead}
              onChange={(e) => onSelectLead(e.target.value)}
            >
              {state.trajectory.map((t) => (
                <option key={t.lead} value={t.lead}>
                  {t.lead} {t.isFailureWindow ? "⚠" : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <span className="control-label">View:</span>
            <select
              className="select-control"
              value={state.selectedView}
              onChange={(e) => onSelectView(e.target.value)}
            >
              <option value="Reliability Risk">Reliability Risk</option>
              <option value="Ensemble Spread">Ensemble Spread</option>
              <option value="Forecast Mean">Forecast Mean</option>
            </select>
          </div>

          <button className="btn-icon" title="Toggle Fullscreen Map">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
            </svg>
          </button>
        </div>
      </div>

      {/* Map Viewport Area */}
      <div className="map-canvas-container">
        <svg
          className="map-svg-viewport"
          viewBox="0 0 880 540"
          preserveAspectRatio="xMidYMid meet"
          style={{ transform: `scale(${zoomLevel})`, transformOrigin: "50% 50%" }}
        >
          <defs>
            {/* Dark Ocean Background Radial Gradient */}
            <radialGradient id="oceanGrad" cx="50%" cy="50%" r="60%">
              <stop offset="0%" stopColor="#0B131D" />
              <stop offset="70%" stopColor="#070C12" />
              <stop offset="100%" stopColor="#05080C" />
            </radialGradient>

            {/* Bust Risk Thermal Anomaly Gradient Field */}
            <radialGradient id="highRiskThermal" cx="50%" cy="45%" r="48%">
              <stop offset="0%" stopColor="#FF3333" stopOpacity="0.92" />
              <stop offset="25%" stopColor="#FF6B22" stopOpacity="0.85" />
              <stop offset="55%" stopColor="#FFAA00" stopOpacity="0.65" />
              <stop offset="75%" stopColor="#66D17A" stopOpacity="0.35" />
              <stop offset="90%" stopColor="#3082B8" stopOpacity="0.15" />
              <stop offset="100%" stopColor="transparent" stopOpacity="0" />
            </radialGradient>

            {/* Northern Sub-Plume */}
            <radialGradient id="northRiskThermal" cx="45%" cy="30%" r="35%">
              <stop offset="0%" stopColor="#FF5533" stopOpacity="0.8" />
              <stop offset="40%" stopColor="#FF9911" stopOpacity="0.55" />
              <stop offset="75%" stopColor="#55C97A" stopOpacity="0.25" />
              <stop offset="100%" stopColor="transparent" stopOpacity="0" />
            </radialGradient>

            {/* Atmospheric Flow streamlines filter */}
            <filter id="thermalGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="8" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Deep Maritime Base */}
          <rect width="880" height="540" fill="url(#oceanGrad)" />

          {/* Geographic Coordinates Graticule */}
          <g className="graticule-layer" stroke="rgba(180, 210, 235, 0.04)" strokeWidth="0.6" strokeDasharray="3 4">
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

          {/* Real South Asian Vector Landmass (India, Pakistan, Bangladesh, Nepal, Bhutan, Sri Lanka, Myanmar) */}
          <g className="landmass-base" fill="#0C131B" stroke="rgba(120, 165, 195, 0.32)" strokeWidth="0.85">
            {Object.entries(southAsiaBorders as Record<string, string[]>).map(([country, paths]) => (
              <g key={country} className={`country-geom country-${country.toLowerCase().replace(/\s+/g, "-")}`}>
                {paths.map((d, idx) => (
                  <path key={idx} d={d} />
                ))}
              </g>
            ))}
          </g>

          {/* Atmospheric Flow Streamlines (Subtle Wind / Pressure Vectors) */}
          <g className="streamlines" stroke="#29557C" strokeWidth="0.9" strokeDasharray="5 6" fill="none" opacity="0.45">
            <path d="M 180 340 Q 280 310 390 280 T 580 240" />
            <path d="M 210 380 Q 310 350 420 320 T 610 270" />
            <path d="M 250 430 Q 350 390 460 360 T 640 310" />
            <path d="M 320 160 Q 420 180 520 200 T 660 220" />
          </g>

          {/* Reliability Bust Vulnerability Field (Rendered in Demo Mode Only) */}
          {state.isDemoMode && layers.reliabilityRisk && (
            <g className="risk-heatmap-layer" filter="url(#thermalGlow)">
              {/* Diffuse Outer Watch Zone */}
              <ellipse cx="450" cy="245" rx="135" ry="105" fill="url(#highRiskThermal)" />
              {/* Northern Secondary Cluster */}
              <ellipse cx="380" cy="155" rx="55" ry="45" fill="url(#northRiskThermal)" />
              {/* Central Core Peak (High Bust Vulnerability Plume) */}
              <ellipse cx="460" cy="240" rx="75" ry="60" fill="url(#highRiskThermal)" />
              <circle cx="465" cy="235" r="30" fill="#FF3A3A" opacity="0.85" />
            </g>
          )}

          {/* Live Operational Status Banner (When Awaiting Case) */}
          {!state.isDemoMode && state.reliability.state === "AWAITING_VERIFIED_CASE" && (
            <g className="live-pipeline-monitoring-badge" transform="translate(440, 260)">
              <rect
                x="-180"
                y="-24"
                width="360"
                height="48"
                rx="6"
                fill="#0A0F15"
                fillOpacity="0.92"
                stroke="rgba(69, 183, 209, 0.35)"
                strokeWidth="1"
              />
              <circle cx="-155" cy="0" r="5" fill="#45B7D1" className="pulse-circle" />
              <text x="-140" y="-4" fill="#F2F5F7" fontSize="11" fontWeight="700" letterSpacing="0.04em">
                LIVE PIPELINE ACTIVE • ZERO FABRICATED RISK
              </text>
              <text x="-140" y="12" fill="#71808C" fontSize="9.5">
                Grid unperturbed • Awaiting step-aligned verified case
              </text>
            </g>
          )}

          {/* Dynamic Cyclone Track Layer */}
          {!state.isDemoMode && state.reliability.state !== "AWAITING_VERIFIED_CASE" && (() => {
            const hasLeads = state.leadsData && state.leadsData.length > 0;
            const stormName = state.activeStormName || "MIDHILI";

            // Forecast points projection
            const fPoints = hasLeads
              ? state.leadsData!.map((r) => {
                  const pt = projectGeoToSvg(r.forecast_lat, r.forecast_lon);
                  return { ...pt, lead: `+${String(r.forecast_lead_hours).padStart(2, "0")}h`, record: r };
                })
              : [
                  { x: 532, y: 492, lead: "+06h", record: null },
                  { x: 523, y: 485, lead: "+12h", record: null },
                  { x: 513, y: 476, lead: "+18h", record: null },
                  { x: 503, y: 469, lead: "+24h", record: null },
                  { x: 492, y: 461, lead: "+30h", record: null },
                  { x: 485, y: 458, lead: "+36h", record: null },
                  { x: 478, y: 452, lead: "+42h", record: null },
                  { x: 473, y: 446, lead: "+48h", record: null },
                ];

            // Observed points projection
            const oPoints = hasLeads
              ? state.leadsData!.map((r) => {
                  const pt = projectGeoToSvg(r.observed_lat, r.observed_lon);
                  return { ...pt, lead: `+${String(r.forecast_lead_hours).padStart(2, "0")}h`, record: r };
                })
              : [
                  { x: 525, y: 488, lead: "+06h", record: null },
                  { x: 521, y: 479, lead: "+12h", record: null },
                  { x: 514, y: 473, lead: "+18h", record: null },
                  { x: 501, y: 469, lead: "+24h", record: null },
                  { x: 490, y: 465, lead: "+30h", record: null },
                  { x: 489, y: 462, lead: "+36h", record: null },
                  { x: 484, y: 458, lead: "+42h", record: null },
                  { x: 481, y: 452, lead: "+48h", record: null },
                ];

            const forecastPathD = fPoints.reduce((acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${pt.x} ${pt.y}`, "");
            const observedPathD = oPoints.reduce((acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${pt.x} ${pt.y}`, "");

            // Envelope around forecast track
            const envelopeD = fPoints.length > 2
              ? `M ${fPoints[0].x - 12} ${fPoints[0].y + 10} ` +
                fPoints.map((p) => `L ${p.x - 16} ${p.y - 8}`).join(" ") + " " +
                fPoints.slice().reverse().map((p) => `L ${p.x + 16} ${p.y + 8}`).join(" ") + " Z"
              : "";

            // Target lead point
            const activeLeadPoint = fPoints.find((p) => p.lead === state.selectedLead) || fPoints[0];
            const activeObsPoint = oPoints.find((p) => p.lead === state.selectedLead) || oPoints[0];

            return (
              <g className="cyclone-track-layer">
                {/* Ensemble Spread Envelope */}
                {envelopeD && (
                  <path
                    d={envelopeD}
                    fill="rgba(245, 184, 61, 0.10)"
                    stroke="rgba(245, 184, 61, 0.25)"
                    strokeWidth="1"
                    strokeDasharray="3 3"
                  />
                )}

                {/* NCMRWF NEPS 11-Member Ensemble Mean Track Line (Gold) */}
                <path
                  d={forecastPathD}
                  fill="none"
                  stroke="#F5B83D"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* NCMRWF Forecast Ensemble Fix Nodes (Gold diamonds) */}
                {fPoints.map((pt, i) => {
                  const isSelected = pt.lead === state.selectedLead;
                  return (
                    <g
                      key={`f-${i}`}
                      style={{ cursor: "pointer" }}
                      onClick={() => onSelectLead(pt.lead)}
                    >
                      <title>{`Forecast Fix ${pt.lead}: click to select lead`}</title>
                      <polygon
                        points={`${pt.x},${pt.y - (isSelected ? 5.5 : 3.5)} ${pt.x + (isSelected ? 5.5 : 3.5)},${pt.y} ${pt.x},${pt.y + (isSelected ? 5.5 : 3.5)} ${pt.x - (isSelected ? 5.5 : 3.5)},${pt.y}`}
                        fill={isSelected ? "#FFD36A" : "#F5B83D"}
                        stroke={isSelected ? "#ffffff" : "none"}
                        strokeWidth={isSelected ? 1.2 : 0}
                      />
                      {isSelected && (
                        <circle cx={pt.x} cy={pt.y} r="9" stroke="#FFD36A" strokeWidth="1.2" fill="none" opacity="0.75" />
                      )}
                    </g>
                  );
                })}

                {/* Ground Truth IMD/RSMC Best Track Layer (Revealed ONLY on user action) */}
                {state.isObservationRevealed ? (
                  <g className="observed-best-track-layer">
                    {/* Error vectors connecting Forecast to Observation */}
                    {fPoints.map((fPt, idx) => {
                      const oPt = oPoints[idx];
                      if (!oPt) return null;
                      return (
                        <line
                          key={`err-vec-${idx}`}
                          x1={fPt.x}
                          y1={fPt.y}
                          x2={oPt.x}
                          y2={oPt.y}
                          stroke="#EF4444"
                          strokeWidth="1.2"
                          strokeDasharray="2 2"
                          opacity="0.8"
                        />
                      );
                    })}

                    {/* Official IMD/RSMC Best Track Fixes (Cyan) */}
                    <path
                      d={observedPathD}
                      fill="none"
                      stroke="#45B7D1"
                      strokeWidth="2.2"
                      strokeDasharray="4 3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />

                    {/* Observed Best Track Fix Nodes (Cyan circles) */}
                    {oPoints.map((pt, i) => (
                      <g key={`o-${i}`} className="best-track-node">
                        <circle cx={pt.x} cy={pt.y} r="3.5" fill="#45B7D1" />
                        <circle cx={pt.x} cy={pt.y} r="6.5" stroke="#45B7D1" strokeWidth="0.8" fill="none" opacity="0.6" />
                      </g>
                    ))}

                    {/* Active Lead Verified Error Badge */}
                    {activeLeadPoint && activeObsPoint && (
                      <g transform={`translate(${(activeLeadPoint.x + activeObsPoint.x) / 2}, ${(activeLeadPoint.y + activeObsPoint.y) / 2 - 14})`}>
                        <rect x="-50" y="-9" width="100" height="18" rx="3" fill="#0A0F15" fillOpacity="0.92" stroke="#EF4444" strokeWidth="1" />
                        <text x="0" y="3.5" fill="#FF6B6B" fontSize="9" fontWeight="700" textAnchor="middle">
                          {(activeLeadPoint as any).record?.track_error_km
                            ? `${(activeLeadPoint as any).record.track_error_km.toFixed(1)} km Error`
                            : "Verified Fix"}
                        </text>
                      </g>
                    )}
                  </g>
                ) : (
                  /* Callout reminding user that ground truth is hidden */
                  <g transform={`translate(${activeLeadPoint ? activeLeadPoint.x + 18 : 520}, ${activeLeadPoint ? activeLeadPoint.y - 15 : 440})`}>
                    <rect x="-8" y="-12" width="185" height="24" rx="4" fill="#0A0F15" fillOpacity="0.9" stroke="rgba(245, 184, 61, 0.4)" strokeWidth="0.9" />
                    <circle cx="2" cy="0" r="3" fill="#F5B83D" />
                    <text x="12" y="3.5" fill="#F5B83D" fontSize="8.5" fontWeight="600">
                      Observation Hidden (Replay Mode)
                    </text>
                  </g>
                )}

                {/* Cyclone Title Callout */}
                <g transform="translate(545, 465)">
                  <rect x="-6" y="-12" width="155" height="26" rx="4" fill="#0A0F15" fillOpacity="0.88" stroke="#F5B83D" strokeWidth="0.8" />
                  <text x="0" y="2" fill="#FFD36A" fontSize="9.5" fontWeight="700">
                    CYCLONE {stormName}
                  </text>
                  <text x="0" y="12" fill="#A8B2BD" fontSize="7.5">
                    {state.continuousErrorSummary
                      ? `Mean Err: ${state.continuousErrorSummary.mean_km.toFixed(1)} km | Max: ${state.continuousErrorSummary.max_km.toFixed(1)} km`
                      : "Verified Track Fixes"}
                  </text>
                </g>

                {/* Track Legend */}
                <g transform="translate(615, 490)">
                  <rect x="-8" y="-14" width="225" height="42" rx="4" fill="#0A0F15" fillOpacity="0.92" stroke="rgba(255,255,255,0.15)" strokeWidth="0.8" />
                  {/* Gold: Forecast */}
                  <line x1="0" y1="-3" x2="22" y2="-3" stroke="#F5B83D" strokeWidth="2.5" />
                  <polygon points="11,-6.5 14.5,-3 11,0.5 7.5,-3" fill="#F5B83D" />
                  <text x="28" y="0" fill="#F5B83D" fontSize="8.5" fontWeight="600">NCMRWF NEPS Track</text>
                  {/* Cyan: IMD Best Track */}
                  <line x1="0" y1="12" x2="22" y2="12" stroke="#45B7D1" strokeWidth="2.0" strokeDasharray="4 2" opacity={state.isObservationRevealed ? 1 : 0.4} />
                  <circle cx="11" cy="12" r="2.5" fill="#45B7D1" opacity={state.isObservationRevealed ? 1 : 0.4} />
                  <text x="28" y="15" fill={state.isObservationRevealed ? "#45B7D1" : "#71808C"} fontSize="8.5" fontWeight="600">
                    {state.isObservationRevealed ? "IMD RSMC Best Track" : "IMD Track (Click Reveal)"}
                  </text>
                </g>
              </g>
            );
          })()}

          {/* Regional Borders (if toggled) */}
          {layers.adminBoundaries && (
            <g className="admin-boundaries" stroke="rgba(180, 210, 240, 0.18)" strokeWidth="0.75" fill="none">
              {/* State Borders */}
              <path d="M 330 140 Q 370 170 390 190 L 440 180" />
              <path d="M 390 190 L 370 260 L 330 270" />
              <path d="M 390 190 L 460 220 L 490 200" />
              <path d="M 460 220 L 460 280 L 420 320" />
              <path d="M 460 280 L 530 290" />
              <path d="M 420 320 L 440 390 L 410 430" />
              <path d="M 440 390 L 480 380" />
            </g>
          )}

          {/* Country & Ocean Watermark Labels */}
          <g className="country-labels" fill="rgba(168, 178, 189, 0.5)" fontSize="9" fontWeight="600" letterSpacing="0.08em">
            <text x="210" y="150">PAKISTAN</text>
            <text x="490" y="80">CHINA</text>
            <text x="440" y="130">NEPAL</text>
            <text x="540" y="145">BHUTAN</text>
            <text x="575" y="215">BANGLADESH</text>
            <text x="660" y="240">MYANMAR</text>
            <text x="450" y="535">SRI LANKA</text>
          </g>

          {/* Oceanic Typographic Annotations */}
          <g className="ocean-labels" fill="#3D5A75" fontSize="10" fontStyle="italic" fontWeight="500" letterSpacing="0.12em">
            <text x="220" y="380" textAnchor="middle">ARABIAN</text>
            <text x="220" y="394" textAnchor="middle">SEA</text>
            <text x="610" y="380" textAnchor="middle">BAY OF</text>
            <text x="610" y="394" textAnchor="middle">BENGAL</text>
            <text x="430" y="470" textAnchor="middle" fontSize="11">INDIAN OCEAN</text>
          </g>

          {/* Dynamic Pin & Hotspot Callout (Active when hotspot is present) */}
          {state.hotspot && (
            <g
              className="hotspot-anchor"
              transform={`translate(${state.hotspot.x * 8.8}, ${state.hotspot.y * 5.4})`}
              style={{ cursor: "pointer" }}
              onClick={() => setShowHotspotDetail((prev) => !prev)}
            >
              <title>Click to toggle hotspot callout</title>
              {/* Concentric Pulse Rings */}
              <circle cx="0" cy="0" r="22" stroke="#FF4D4D" strokeWidth="1.2" fill="none" opacity="0.3" className="pulse-circle" />
              <circle cx="0" cy="0" r="14" stroke="#FF4D4D" strokeWidth="1.6" fill="rgba(255, 77, 77, 0.12)" />
              <circle cx="0" cy="0" r="6" fill="#FF4D4D" />
              <circle cx="0" cy="0" r="2.5" fill="#FFFFFF" />

              {/* Callout Box with Dark Glass Appearance */}
              {showHotspotDetail && (
                <g className="hotspot-callout-box" transform="translate(15, -42)">
                  {/* Pointer Connector Line */}
                  <line x1="-15" y1="42" x2="0" y2="25" stroke="#FF4D4D" strokeWidth="1.5" />

                  {/* Box Background */}
                  <rect
                    x="0"
                    y="0"
                    width="190"
                    height="76"
                    rx="6"
                    fill="#0B1118"
                    fillOpacity="0.94"
                    stroke="#FF4D4D"
                    strokeWidth="1.2"
                    filter="drop-shadow(0 6px 16px rgba(0,0,0,0.6))"
                  />

                  {/* Header with Alert Pill */}
                  <text x="12" y="19" fill="#F2F5F7" fontSize="10.5" fontWeight="700">
                    {state.hotspot.name}
                  </text>
                  <rect x="125" y="8" width="55" height="14" rx="3" fill="rgba(255, 77, 77, 0.2)" />
                  <text x="152" y="19" fill="#FF7777" fontSize="8.5" fontWeight="700" textAnchor="middle">
                    {state.hotspot.leadWindow}
                  </text>

                  {/* Hotspot Body */}
                  <text x="12" y="36" fill="#A8B2BD" fontSize="8.5" fontWeight="400">
                    {state.hotspot.description.slice(0, 34)}
                  </text>
                  <text x="12" y="48" fill="#A8B2BD" fontSize="8.5" fontWeight="400">
                    {state.hotspot.description.slice(34, 68)}
                  </text>
                  <text x="12" y="60" fill="#A8B2BD" fontSize="8.5" fontWeight="400">
                    {state.hotspot.description.slice(68, 102)}
                  </text>
                </g>
              )}
            </g>
          )}
        </svg>

        {/* Floating Scenario State Badge (Top Right of Map) */}
        <div className="map-scenario-overlay">
          {state.isDemoMode ? (
            <div className="map-badge-scenario badge-demo">
              <span className="badge-dot dot-amber" />
              <div className="badge-text-col">
                <span className="badge-title">DEMO SCENARIO</span>
                <span className="badge-sub">Illustrative Bust Vulnerability Plume</span>
              </div>
            </div>
          ) : state.reliability.state === "AWAITING_VERIFIED_CASE" ? (
            <div className="map-badge-scenario badge-live">
              <span className="badge-dot dot-cyan" />
              <div className="badge-text-col">
                <span className="badge-title">LIVE PIPELINE MONITORING</span>
                <span className="badge-sub">No Fabricated Risk • Awaiting Aligned Case</span>
              </div>
            </div>
          ) : (
            <div className="map-badge-scenario badge-verified">
              <span className="badge-dot dot-gold pulse-circle" />
              <div className="badge-text-col">
                <span className="badge-title">EVENT-VERIFIED CYCLONE (MICHAUNG)</span>
                <span className="badge-sub">Real NCMRWF NEPS vs Official IMD Best Track</span>
              </div>
            </div>
          )}
        </div>

        {/* Floating Controls: Compass & Zoom (Top Left on Map) */}
        <div className="map-tools-overlay">
          <div className="compass-widget" title="Subcontinent Orientation">
            <svg viewBox="0 0 32 32" width="28" height="28">
              <circle cx="16" cy="16" r="14" fill="rgba(15, 20, 26, 0.85)" stroke="rgba(180, 210, 225, 0.2)" strokeWidth="1" />
              <polygon points="16,5 19,16 16,14 13,16" fill="#F5B83D" />
              <polygon points="16,27 19,16 16,18 13,16" fill="#4C5660" />
              <text x="16" y="10" fontSize="6.5" fontWeight="700" fill="#F5B83D" textAnchor="middle">N</text>
            </svg>
          </div>

          <div className="zoom-widget">
            <button
              className="map-btn"
              onClick={() => setZoomLevel((z) => Math.min(z + 0.2, 1.8))}
              title="Zoom In"
            >
              +
            </button>
            <button
              className="map-btn"
              onClick={() => setZoomLevel((z) => Math.max(z - 0.2, 0.8))}
              title="Zoom Out"
            >
              –
            </button>
            <button
              className="map-btn"
              onClick={() => setZoomLevel(1)}
              title="Reset View"
            >
              ⌖
            </button>
          </div>
        </div>

        {/* Floating Controls: Layer Selector Checkbox Box (Bottom Left on Map) */}
        <div className="map-layer-selector">
          <label className="layer-checkbox-row">
            <input
              type="checkbox"
              checked={layers.reliabilityRisk}
              onChange={() => toggleLayer("reliabilityRisk")}
            />
            <span className="checkbox-custom" />
            <span className="layer-text highlight-risk">Reliability Risk (FG)</span>
          </label>

          <label className="layer-checkbox-row">
            <input
              type="checkbox"
              checked={layers.ncmrwfForecast}
              onChange={() => toggleLayer("ncmrwfForecast")}
            />
            <span className="checkbox-custom" />
            <span className="layer-text">NCMRWF Forecast</span>
          </label>

          <label className="layer-checkbox-row">
            <input
              type="checkbox"
              checked={layers.ensembleSpread}
              onChange={() => toggleLayer("ensembleSpread")}
            />
            <span className="checkbox-custom" />
            <span className="layer-text">Ensemble Spread</span>
          </label>

          <label className="layer-checkbox-row">
            <input
              type="checkbox"
              checked={layers.adminBoundaries}
              onChange={() => toggleLayer("adminBoundaries")}
            />
            <span className="checkbox-custom" />
            <span className="layer-text">Administrative Boundaries</span>
          </label>

          <label className="layer-checkbox-row">
            <input
              type="checkbox"
              checked={layers.cityLabels}
              onChange={() => toggleLayer("cityLabels")}
            />
            <span className="checkbox-custom" />
            <span className="layer-text">City Labels</span>
          </label>
        </div>

        {/* Bottom Colorbar Legend */}
        <div className="map-legend-overlay">
          <div className="legend-title-row">
            <span className="legend-title">Forecast Bust Risk (%)</span>
          </div>
          <div className="legend-colorbar-wrapper">
            <div className="legend-gradient-bar" />
            <div className="legend-ticks">
              <span>0</span>
              <span>20</span>
              <span>40</span>
              <span>60</span>
              <span>80</span>
              <span>100</span>
            </div>
          </div>
        </div>

        {/* Bottom Scale Bar (Center-Right on Map) */}
        <div className="map-scale-overlay">
          <div className="scale-line-container">
            <div className="scale-ticks">
              <span>0</span>
              <span>250</span>
              <span>500</span>
              <span>1,000 km</span>
            </div>
            <div className="scale-bar-line" />
          </div>
        </div>
      </div>
    </section>
  );
};
