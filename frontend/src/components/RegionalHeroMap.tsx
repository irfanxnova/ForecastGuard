import React, { useState } from "react";
import { CanonicalRegionalAssessment, CanonicalReliabilityState } from "../types/dashboard";
import southAsiaBorders from "../data/south_asia_borders.json";
import { projectGeoToSvg } from "../data/casesData";

interface RegionalHeroMapProps {
  assessments: CanonicalRegionalAssessment[];
  selectedRegionId: string;
  onSelectRegion: (regionId: string) => void;
  leadTime: string;
  caseId: string;
  variable: string;
}

interface RegionPolygonDef {
  region_id: string;
  name: string;
  short_label: string;
  center_lat: number;
  center_lon: number;
  coords: [number, number][]; // [lat, lon]
}

// ForecastGuard Predefined Analytical Regions mapped in geographic coordinates
const REGION_POLYGONS: RegionPolygonDef[] = [
  {
    region_id: "MAR_BOB",
    name: "Bay of Bengal Basin",
    short_label: "Bay of Bengal",
    center_lat: 15.2,
    center_lon: 88.0,
    coords: [
      [8.0, 80.0],
      [15.0, 80.0],
      [21.0, 86.5],
      [22.5, 91.0],
      [20.0, 94.0],
      [14.0, 95.0],
      [8.0, 93.0],
    ],
  },
  {
    region_id: "MAR_AS",
    name: "Arabian Sea Basin",
    short_label: "Arabian Sea",
    center_lat: 16.0,
    center_lon: 65.0,
    coords: [
      [8.0, 55.0],
      [16.0, 55.0],
      [24.5, 62.0],
      [24.0, 69.0],
      [20.0, 72.5],
      [12.0, 74.0],
      [8.0, 74.0],
    ],
  },
  {
    region_id: "IND_ENE",
    name: "East & Northeast India",
    short_label: "East & NE India",
    center_lat: 24.5,
    center_lon: 89.5,
    coords: [
      [20.0, 83.0],
      [26.0, 83.0],
      [27.5, 88.0],
      [29.0, 94.0],
      [27.0, 97.0],
      [23.0, 93.0],
      [21.5, 87.0],
    ],
  },
  {
    region_id: "IND_SOU",
    name: "South Peninsular India",
    short_label: "South Peninsula",
    center_lat: 13.5,
    center_lon: 78.5,
    coords: [
      [8.0, 77.0],
      [11.0, 75.0],
      [15.0, 74.0],
      [18.5, 78.0],
      [18.0, 83.5],
      [13.5, 80.5],
      [9.0, 79.5],
    ],
  },
  {
    region_id: "IND_CEN",
    name: "Central India",
    short_label: "Central India",
    center_lat: 22.0,
    center_lon: 79.5,
    coords: [
      [18.0, 73.0],
      [23.0, 73.0],
      [26.0, 78.0],
      [25.5, 84.5],
      [21.5, 86.0],
      [18.5, 80.0],
    ],
  },
  {
    region_id: "IND_WST",
    name: "West Coast & Gujarat",
    short_label: "West Coast / Gujarat",
    center_lat: 21.5,
    center_lon: 71.5,
    coords: [
      [17.5, 73.0],
      [20.0, 72.5],
      [23.5, 68.0],
      [25.0, 71.0],
      [24.0, 74.5],
      [19.0, 74.0],
    ],
  },
  {
    region_id: "IND_NW",
    name: "Northwest India",
    short_label: "Northwest India",
    center_lat: 30.0,
    center_lon: 74.5,
    coords: [
      [24.0, 68.0],
      [28.0, 69.0],
      [34.0, 73.5],
      [36.0, 77.0],
      [31.0, 80.5],
      [26.0, 78.5],
      [24.0, 73.0],
    ],
  },
];

// Helper to convert lat/lon array to SVG path
function polygonToSvgPath(coords: [number, number][]): string {
  if (coords.length === 0) return "";
  const points = coords.map(([lat, lon]) => projectGeoToSvg(lat, lon));
  return "M " + points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" L ") + " Z";
}

// Styling tokens per reliability state
const STATE_STYLES: Record<
  CanonicalReliabilityState,
  {
    fill: string;
    stroke: string;
    badgeBg: string;
    badgeBorder: string;
    badgeText: string;
    label: string;
    icon: string;
  }
> = {
  STABLE: {
    fill: "rgba(34, 197, 94, 0.16)",
    stroke: "#22c55e",
    badgeBg: "rgba(34, 197, 94, 0.20)",
    badgeBorder: "rgba(34, 197, 94, 0.45)",
    badgeText: "#4ade80",
    label: "STABLE",
    icon: "✓",
  },
  WATCH: {
    fill: "rgba(245, 158, 11, 0.20)",
    stroke: "#f59e0b",
    badgeBg: "rgba(245, 158, 11, 0.22)",
    badgeBorder: "rgba(245, 158, 11, 0.50)",
    badgeText: "#fbbf24",
    label: "WATCH",
    icon: "⚠",
  },
  DEGRADING: {
    fill: "rgba(249, 115, 22, 0.25)",
    stroke: "#f97316",
    badgeBg: "rgba(249, 115, 22, 0.28)",
    badgeBorder: "rgba(249, 115, 22, 0.55)",
    badgeText: "#fb923c",
    label: "DEGRADING",
    icon: "⚡",
  },
  HIGH_RISK: {
    fill: "rgba(239, 68, 68, 0.30)",
    stroke: "#ef4444",
    badgeBg: "rgba(239, 68, 68, 0.32)",
    badgeBorder: "rgba(239, 68, 68, 0.60)",
    badgeText: "#f87171",
    label: "HIGH RISK",
    icon: "🚨",
  },
  INSUFFICIENT_EVIDENCE: {
    fill: "url(#insufficientHatch)",
    stroke: "#475569",
    badgeBg: "rgba(71, 85, 105, 0.30)",
    badgeBorder: "rgba(71, 85, 105, 0.50)",
    badgeText: "#94a3b8",
    label: "INSUFFICIENT EVIDENCE",
    icon: "⊘",
  },
};

export const RegionalHeroMap: React.FC<RegionalHeroMapProps> = ({
  assessments,
  selectedRegionId,
  onSelectRegion,
  leadTime,
  caseId,
  variable,
}) => {
  const [hoveredRegionId, setHoveredRegionId] = useState<string | null>(null);

  // Map assessment by region_id
  const assessmentMap = new Map<string, CanonicalRegionalAssessment>();
  assessments.forEach((a) => assessmentMap.set(a.region_id, a));

  return (
    <div className="regional-hero-map-wrapper">
      <div className="map-legend-bar">
        <div className="legend-item">
          <span className="legend-chip stable"></span>
          <span className="legend-label">Stable</span>
        </div>
        <div className="legend-item">
          <span className="legend-chip watch"></span>
          <span className="legend-label">Watch</span>
        </div>
        <div className="legend-item">
          <span className="legend-chip degrading"></span>
          <span className="legend-label">Degrading</span>
        </div>
        <div className="legend-item">
          <span className="legend-chip high-risk"></span>
          <span className="legend-label">High Risk</span>
        </div>
        <div className="legend-item">
          <span className="legend-chip insufficient"></span>
          <span className="legend-label">Insufficient Evidence</span>
        </div>
        <div className="legend-meta">
          <span>Click any region to inspect telemetry</span>
        </div>
      </div>

      <div className="map-canvas-container">
        <svg
          className="map-svg-viewport"
          viewBox="0 0 880 540"
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            {/* Dark Ocean Background Gradient */}
            <radialGradient id="oceanGrad" cx="50%" cy="50%" r="60%">
              <stop offset="0%" stopColor="#0B131D" />
              <stop offset="70%" stopColor="#070C12" />
              <stop offset="100%" stopColor="#05080C" />
            </radialGradient>

            {/* Pattern for Insufficient Evidence regions */}
            <pattern
              id="insufficientHatch"
              width="10"
              height="10"
              patternTransform="rotate(45 0 0)"
              patternUnits="userSpaceOnUse"
            >
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="10"
                stroke="rgba(100, 116, 139, 0.22)"
                strokeWidth="2"
              />
            </pattern>

            {/* Region Selection Glow Filter */}
            <filter id="selectionGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#F5B83D" floodOpacity="0.8" />
            </filter>
          </defs>

          {/* 1. Deep Ocean Canvas */}
          <rect width="880" height="540" fill="url(#oceanGrad)" />

          {/* 2. Synoptic Latitude / Longitude Reference Grid */}
          <g className="grid-lines" opacity="0.18">
            {[10, 15, 20, 25, 30, 35].map((lat) => {
              const p = projectGeoToSvg(lat, 84.2);
              return (
                <g key={`lat-${lat}`}>
                  <line x1="30" y1={p.y} x2="850" y2={p.y} stroke="#38BDF8" strokeWidth="0.5" strokeDasharray="3 5" />
                  <text x="35" y={p.y - 3} fill="#64748B" fontSize="9" fontFamily="monospace">
                    {lat}°N
                  </text>
                </g>
              );
            })}
            {[60, 70, 80, 90].map((lon) => {
              const p = projectGeoToSvg(20, lon);
              return (
                <g key={`lon-${lon}`}>
                  <line x1={p.x} y1="20" x2={p.x} y2="520" stroke="#38BDF8" strokeWidth="0.5" strokeDasharray="3 5" />
                  <text x={p.x + 3} y="532" fill="#64748B" fontSize="9" fontFamily="monospace">
                    {lon}°E
                  </text>
                </g>
              );
            })}
          </g>

          {/* 3. Base Country Landmasses */}
          <g className="landmass-layer">
            {Object.entries(southAsiaBorders).map(([country, paths]) => (
              <g key={country} className="country-group" opacity="0.65">
                {paths.map((d, i) => (
                  <path
                    key={i}
                    d={d}
                    fill="#111B27"
                    stroke="#1E2C3D"
                    strokeWidth="1.2"
                  />
                ))}
              </g>
            ))}
          </g>

          {/* 4. Meteorological Regional Reliability Polygons */}
          <g className="regional-reliability-layer">
            {REGION_POLYGONS.map((poly) => {
              const assessment = assessmentMap.get(poly.region_id);
              const state: CanonicalReliabilityState =
                assessment?.reliability_state || "INSUFFICIENT_EVIDENCE";
              const style = STATE_STYLES[state];
              const isSelected = selectedRegionId === poly.region_id;
              const isHovered = hoveredRegionId === poly.region_id;
              const svgPath = polygonToSvgPath(poly.coords);
              const center = projectGeoToSvg(poly.center_lat, poly.center_lon);

              return (
                <g
                  key={poly.region_id}
                  className={`region-interactive-group ${isSelected ? "selected" : ""}`}
                  onClick={() => onSelectRegion(poly.region_id)}
                  onMouseEnter={() => setHoveredRegionId(poly.region_id)}
                  onMouseLeave={() => setHoveredRegionId(null)}
                  style={{ cursor: "pointer" }}
                >
                  {/* Region Polygon Fill */}
                  <path
                    d={svgPath}
                    fill={style.fill}
                    stroke={isSelected ? "#F5B83D" : style.stroke}
                    strokeWidth={isSelected ? 2.5 : isHovered ? 2.0 : 1.2}
                    strokeDasharray={state === "INSUFFICIENT_EVIDENCE" ? "5 4" : "none"}
                    filter={isSelected ? "url(#selectionGlow)" : "none"}
                    opacity={isSelected ? 1.0 : isHovered ? 0.95 : 0.85}
                    className="region-boundary-path"
                  />

                  {/* Region Center Pill / State Badge */}
                  <g
                    transform={`translate(${center.x}, ${center.y})`}
                    className="region-center-badge"
                  >
                    {/* Badge Background */}
                    <rect
                      x="-65"
                      y="-18"
                      width="130"
                      height="36"
                      rx="6"
                      fill="#0B131E"
                      fillOpacity="0.92"
                      stroke={isSelected ? "#F5B83D" : style.stroke}
                      strokeWidth={isSelected ? 1.8 : 1.0}
                    />

                    {/* Region Short Title */}
                    <text
                      x="0"
                      y="-4"
                      textAnchor="middle"
                      fill="#E2E8F0"
                      fontSize="10"
                      fontWeight="600"
                      fontFamily="Inter, sans-serif"
                    >
                      {poly.short_label}
                    </text>

                    {/* Reliability State / Probability Tag */}
                    <text
                      x="0"
                      y="11"
                      textAnchor="middle"
                      fill={style.badgeText}
                      fontSize="9"
                      fontWeight="700"
                      fontFamily="monospace"
                    >
                      {assessment?.bust_probability !== null && assessment?.bust_probability !== undefined
                        ? `${style.icon} ${style.label} · ${Math.round(assessment.bust_probability * 100)}%`
                        : `${style.icon} ${style.label}`}
                    </text>
                  </g>
                </g>
              );
            })}
          </g>

          {/* 5. Map Canvas Metadata Stamp */}
          <g transform="translate(25, 495)" opacity="0.85">
            <rect x="0" y="0" width="220" height="30" rx="4" fill="#080E16" stroke="#1E293B" strokeWidth="0.8" />
            <text x="10" y="14" fill="#94A3B8" fontSize="9" fontFamily="monospace">
              CASE: {caseId} · LEAD: {leadTime}
            </text>
            <text x="10" y="24" fill="#64748B" fontSize="8" fontFamily="monospace">
              VARIABLE: {variable}
            </text>
          </g>
        </svg>
      </div>
    </div>
  );
};
