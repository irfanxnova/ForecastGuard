import React from "react";
import { DashboardState } from "../types/dashboard";

interface AtmosphericContextProps {
  state: DashboardState;
}

export const AtmosphericContext: React.FC<AtmosphericContextProps> = ({ state }) => {
  return (
    <section className="panel atmospheric-panel" aria-label="Atmospheric Context">
      {/* Panel Header */}
      <div className="panel-header">
        <div className="panel-title-group">
          <h2 className="panel-title">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#45B7D1" strokeWidth="2">
              <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" />
            </svg>
            ATMOSPHERIC CONTEXT (NCMRWF {state.selectedLead})
          </h2>
          <span className="panel-subtitle">500 hPa Geopotential Height & Anomaly</span>
        </div>
      </div>

      {/* Atmospheric Visualization Canvas */}
      <div className="atmospheric-content-wrapper">
        <div className="atmospheric-map-container">
          <svg className="atmospheric-svg" viewBox="0 0 280 145" preserveAspectRatio="xMidYMid meet">
            <defs>
              {/* Thermal Anomaly Multi-Stop Gradient */}
              <radialGradient id="troughAnomaly" cx="48%" cy="50%" r="45%">
                <stop offset="0%" stopColor="#2563EB" stopOpacity="0.85" />
                <stop offset="30%" stopColor="#38BDF8" stopOpacity="0.65" />
                <stop offset="60%" stopColor="#34D399" stopOpacity="0.45" />
                <stop offset="80%" stopColor="#FBBF24" stopOpacity="0.55" />
                <stop offset="100%" stopColor="#EF4444" stopOpacity="0.75" />
              </radialGradient>
            </defs>

            {/* Base Field */}
            <rect width="280" height="145" fill="#091018" />

            {/* Regional Land Contour Outline */}
            <path
              d="M 100 20 Q 140 25 180 35 L 200 65 L 180 85 Q 160 120 140 135 L 125 110 Q 100 80 80 50 Z"
              fill="#0E1722"
              stroke="rgba(180, 210, 240, 0.25)"
              strokeWidth="0.8"
            />

            {/* Colorized Height Anomaly Wave */}
            <ellipse cx="138" cy="72" rx="75" ry="48" fill="url(#troughAnomaly)" />

            {/* Isobar / Geopotential Contours */}
            <g fill="none" stroke="rgba(255, 255, 255, 0.45)" strokeWidth="0.9">
              <path d="M 40 40 Q 130 90 240 40" />
              <path d="M 40 60 Q 135 110 240 60" />
              <path d="M 40 80 Q 140 128 240 80" />
              <path d="M 50 100 Q 140 145 230 100" />
            </g>

            {/* Trough Axis & Cyclonic 'L' Center */}
            <g transform="translate(138, 80)">
              <circle cx="0" cy="0" r="10" fill="#0B131D" stroke="#38BDF8" strokeWidth="1.2" />
              <text x="0" y="4" fill="#38BDF8" fontSize="11" fontWeight="800" textAnchor="middle">
                L
              </text>
            </g>

            {/* Wind Vector Arrows */}
            <g stroke="#67E8F9" strokeWidth="1" opacity="0.6">
              <path d="M 90 70 L 105 82" />
              <path d="M 120 95 L 138 98" />
              <path d="M 155 95 L 170 82" />
              <path d="M 175 65 L 185 50" />
            </g>
          </svg>

          {/* Colorbar Scale on Right */}
          <div className="atmospheric-scale-col">
            <span className="scale-unit">Anomaly (m)</span>
            <div className="scale-rainbow-bar" />
            <div className="scale-labels">
              <span>+300</span>
              <span>+200</span>
              <span>+100</span>
              <span>0</span>
              <span>-100</span>
              <span>-200</span>
              <span>-300</span>
            </div>
          </div>
        </div>

        {/* Informative Meteorological Caption */}
        <div className="atmospheric-caption">
          Atmospheric pattern indicates an anomalous trough over central India.
        </div>
      </div>
    </section>
  );
};
