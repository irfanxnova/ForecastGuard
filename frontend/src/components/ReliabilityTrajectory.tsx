import React, { useState } from "react";
import { DashboardState, TrajectoryPoint } from "../types/dashboard";

interface ReliabilityTrajectoryProps {
  state: DashboardState;
  onSelectLead?: (lead: string) => void;
}

export const ReliabilityTrajectory: React.FC<ReliabilityTrajectoryProps> = ({
  state,
  onSelectLead,
}) => {
  const [hoveredPoint, setHoveredPoint] = useState<TrajectoryPoint | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);

  const { trajectory } = state;

  // Chart dimensions inside SVG coordinate system (width: 580, height: 210)
  const width = 580;
  const height = 210;
  const padLeft = 45;
  const padRight = 25;
  const padTop = 30;
  const padBottom = 35;

  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  // X coordinate calculation
  const getX = (index: number) => padLeft + (index / (trajectory.length - 1)) * chartW;
  // Y coordinate calculation (score 0 at bottom, 100 at top)
  const getY = (score: number) => padTop + chartH - (score / 100) * chartH;

  // Color helper based on state
  const getColor = (s: string) => {
    switch (s) {
      case "STABLE":
        return "#55D98A";
      case "WATCH":
        return "#F5C542";
      case "DEGRADING":
        return "#FF922B";
      case "HAZARDOUS":
        return "#FF4D4D";
      default:
        return "#71808C";
    }
  };

  // Build SVG path string with smooth curves (Demo Mode only)
  const hasScores = trajectory.some((t) => typeof t.score === "number" && t.score !== null);
  const points = hasScores
    ? trajectory.map((p, i) => ({ x: getX(i), y: getY(p.score ?? 50), ...p }))
    : [];

  const pathData = points.length > 0 ? points.reduce((acc, curr, i, arr) => {
    if (i === 0) return `M ${curr.x} ${curr.y}`;
    const prev = arr[i - 1];
    const cx1 = prev.x + (curr.x - prev.x) / 2;
    const cy1 = prev.y;
    const cx2 = prev.x + (curr.x - prev.x) / 2;
    const cy2 = curr.y;
    return `${acc} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${curr.x} ${curr.y}`;
  }, "") : "";

  // Area under path
  const areaData = points.length > 0
    ? `${pathData} L ${points[points.length - 1].x} ${padTop + chartH} L ${points[0].x} ${padTop + chartH} Z`
    : "";

  // Positions for D+3 marker and D+4 to D+5 failure window
  const d3Index = trajectory.findIndex((t) => t.lead === "D+3");
  const d4Index = trajectory.findIndex((t) => t.lead === "D+4");
  const d5Index = trajectory.findIndex((t) => t.lead === "D+5");

  const d3X = d3Index >= 0 ? getX(d3Index) : 0;
  const d4X = d4Index >= 0 ? getX(d4Index) : 0;
  const d5X = d5Index >= 0 ? getX(d5Index) : 0;

  return (
    <section className="panel trajectory-panel" aria-label="Reliability Trajectory">
      {/* Panel Header */}
      <div className="panel-header">
        <div className="panel-title-group">
          <h2 className="panel-title">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#F5B83D" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            RELIABILITY TRAJECTORY
          </h2>
          <span className="panel-subtitle">Forecast reliability evolution across lead times</span>
          {state.isDemoMode && (
            <span className="demo-indicator-pill">DEMO SCENARIO</span>
          )}
        </div>

        <div className="panel-controls">
          <select className="select-control" defaultValue="Reliability Score">
            <option value="Reliability Score">View: Reliability Score</option>
            <option value="Bust Probability">View: Bust Probability</option>
            <option value="Ensemble Spread">View: Ensemble Spread</option>
          </select>

          {/* Semantic Legend */}
          <div className="trajectory-legend">
            <span className="legend-item">
              <span className="dot dot-stable" /> Stable
            </span>
            <span className="legend-item">
              <span className="dot dot-watch" /> Watch
            </span>
            <span className="legend-item">
              <span className="dot dot-degrading" /> Degrading
            </span>
            <span className="legend-item">
              <span className="dot dot-hazardous" /> Hazardous
            </span>
          </div>
        </div>
      </div>

      {/* SVG Chart Container */}
      <div className="trajectory-chart-wrapper">
        <svg
          className="trajectory-svg"
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="none"
        >
          <defs>
            {/* Gradient under curve */}
            <linearGradient id="trajectoryAreaGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#F5B83D" stopOpacity="0.25" />
              <stop offset="60%" stopColor="#FF4D4D" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#080A0D" stopOpacity="0.0" />
            </linearGradient>

            {/* Stroke multi-stop gradient along lead times */}
            <linearGradient id="curveGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#55D98A" />
              <stop offset="25%" stopColor="#55D98A" />
              <stop offset="35%" stopColor="#F5C542" />
              <stop offset="55%" stopColor="#FF922B" />
              <stop offset="75%" stopColor="#FF4D4D" />
              <stop offset="100%" stopColor="#FF3333" />
            </linearGradient>
          </defs>

          {/* Horizontal Grid Lines */}
          {[0, 20, 40, 60, 80, 100].map((val) => {
            const y = getY(val);
            return (
              <g key={val}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - padRight}
                  y2={y}
                  stroke={val === 0 ? "rgba(180, 210, 225, 0.18)" : "rgba(180, 210, 225, 0.06)"}
                  strokeDasharray={val === 0 ? "none" : "2 3"}
                  strokeWidth="0.8"
                />
                <text
                  x={padLeft - 8}
                  y={y + 3.5}
                  fill="#6F7C88"
                  fontSize="9"
                  textAnchor="end"
                  fontFamily="Inter"
                >
                  {val}
                </text>
              </g>
            );
          })}

          {/* Demo Scenario Trajectory Rendering */}
          {state.isDemoMode && hasScores && (
            <>
              {/* Shaded Expected Failure Window (D+4 to D+5) */}
              {d4X > 0 && d5X > 0 && (
                <g className="failure-window-band">
                  <rect
                    x={d4X - 16}
                    y={padTop}
                    width={d5X - d4X + 32}
                    height={chartH}
                    fill="rgba(255, 77, 77, 0.09)"
                    stroke="rgba(255, 77, 77, 0.22)"
                    strokeDasharray="3 3"
                    strokeWidth="1"
                    rx="3"
                  />
                  <rect
                    x={d4X - 10}
                    y={padTop + chartH - 24}
                    width={d5X - d4X + 20}
                    height="18"
                    rx="3"
                    fill="rgba(15, 20, 26, 0.85)"
                    stroke="rgba(255, 77, 77, 0.4)"
                  />
                  <text
                    x={(d4X + d5X) / 2}
                    y={padTop + chartH - 12}
                    fill="#FF922B"
                    fontSize="7.8"
                    fontWeight="600"
                    textAnchor="middle"
                  >
                    Expected failure window
                  </text>
                  <text
                    x={(d4X + d5X) / 2}
                    y={padTop + chartH - 3}
                    fill="#FF6666"
                    fontSize="7"
                    fontWeight="500"
                    textAnchor="middle"
                  >
                    D+4 – D+5
                  </text>
                </g>
              )}

              {/* D+3 First Actionable Signal Marker */}
              {d3X > 0 && (
                <g className="actionable-signal-marker">
                  <line
                    x1={d3X}
                    y1={padTop}
                    x2={d3X}
                    y2={padTop + chartH}
                    stroke="#F5B83D"
                    strokeWidth="1.2"
                    strokeDasharray="3 2.5"
                  />
                  {/* Callout Capsule */}
                  <g transform={`translate(${d3X - 44}, ${padTop + 62})`}>
                    <rect
                      x="0"
                      y="0"
                      width="88"
                      height="26"
                      rx="4"
                      fill="#0B0F14"
                      stroke="#F5B83D"
                      strokeWidth="1.1"
                      filter="drop-shadow(0 2px 6px rgba(0,0,0,0.5))"
                    />
                    <text x="44" y="11" fill="#FFD36A" fontSize="8.5" fontWeight="700" textAnchor="middle">
                      D+3
                    </text>
                    <text x="44" y="21" fill="#A8B2BD" fontSize="7.2" fontWeight="500" textAnchor="middle">
                      First actionable signal
                    </text>
                  </g>
                </g>
              )}

              {/* Shaded Area Under Curve */}
              <path d={areaData} fill="url(#trajectoryAreaGrad)" />

              {/* The Main Trajectory Curve */}
              <path
                d={pathData}
                fill="none"
                stroke="url(#curveGradient)"
                strokeWidth="2.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </>
          )}

          {/* Live Pipeline State Notice */}
          {!state.isDemoMode && (
            <g className="live-trajectory-notice" transform={`translate(${width / 2}, ${height / 2})`}>
              <rect
                x="-190"
                y="-26"
                width="380"
                height="52"
                rx="6"
                fill="#0B121A"
                fillOpacity="0.95"
                stroke="rgba(69, 183, 209, 0.3)"
                strokeWidth="1"
              />
              <circle cx="-165" cy="0" r="4" fill="#45B7D1" className="pulse-circle" />
              <text x="-150" y="-4" fill="#F2F5F7" fontSize="10.5" fontWeight="700">
                TRAJECTORY DYNAMICAL MONITORING ACTIVE
              </text>
              <text x="-150" y="12" fill="#71808C" fontSize="8.8">
                Calibrated score trajectory will render once aligned verification cases are processed
              </text>
            </g>
          )}

          {/* Interactive Trajectory Data Points */}
          {points.map((p) => {
            const isHovered = hoveredPoint?.lead === p.lead;
            const ptColor = getColor(p.state);

            return (
              <g
                key={p.lead}
                className="trajectory-point-node"
                style={{ cursor: "pointer" }}
                onClick={() => onSelectLead && onSelectLead(p.lead)}
                onMouseEnter={() => {
                  setHoveredPoint(p);
                  setTooltipPos({ x: p.x, y: p.y });
                }}
                onMouseLeave={() => setHoveredPoint(null)}
              >
                {/* Halo if selected/hovered */}
                {isHovered && (
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r="12"
                    fill={ptColor}
                    opacity="0.25"
                    className="pulse-circle"
                  />
                )}
                {/* Node Ring */}
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={isHovered ? "6.5" : "4.5"}
                  fill="#080A0D"
                  stroke={ptColor}
                  strokeWidth={isHovered ? "3" : "2"}
                  style={{ transition: "all 0.2s ease" }}
                />
                {/* Node Center Dot */}
                <circle cx={p.x} cy={p.y} r="2" fill={ptColor} />

                {/* X-Axis Lead Labels */}
                <text
                  x={p.x}
                  y={padTop + chartH + 18}
                  fill={isHovered ? "#F2F5F7" : "#A8B2BD"}
                  fontSize="9.5"
                  fontWeight={isHovered ? "700" : "500"}
                  textAnchor="middle"
                >
                  {p.lead}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip */}
        {hoveredPoint && tooltipPos && (
          <div
            className="trajectory-tooltip"
            style={{
              left: `${(tooltipPos.x / width) * 100}%`,
              top: `${(tooltipPos.y / height) * 100}%`,
            }}
          >
            <div className="tooltip-header">
              <span className="tooltip-lead">{hoveredPoint.lead}</span>
              <span className={`tooltip-state badge badge-${hoveredPoint.state.toLowerCase()}`}>
                {hoveredPoint.state}
              </span>
            </div>
            <div className="tooltip-score">
              Reliability: <strong>{hoveredPoint.score}%</strong>
            </div>
            {hoveredPoint.description && (
              <div className="tooltip-desc">{hoveredPoint.description}</div>
            )}
          </div>
        )}
      </div>
    </section>
  );
};
