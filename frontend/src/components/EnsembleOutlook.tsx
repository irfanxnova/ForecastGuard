import React from "react";
import { DashboardState } from "../types/dashboard";

interface EnsembleOutlookProps {
  state: DashboardState;
}

export const EnsembleOutlook: React.FC<EnsembleOutlookProps> = ({ state }) => {
  const { ensembleSeries, selectedLead } = state;

  const hasSeries = ensembleSeries.length > 1;

  // Chart coordinates
  const width = 310;
  const height = 140;
  const padL = 34;
  const padR = 12;
  const padT = 16;
  const padB = 26;

  const chartW = width - padL - padR;
  const chartH = height - padT - padB;
  const maxVal = 300;

  const getX = (i: number) => padL + (i / Math.max(1, ensembleSeries.length - 1)) * chartW;
  const getY = (val: number) => padT + chartH - (Math.min(val, maxVal) / maxVal) * chartH;

  // Mean path
  const meanPath = hasSeries
    ? ensembleSeries.reduce((acc, curr, i) => {
        const x = getX(i);
        const y = getY(curr.mean);
        return i === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
      }, "")
    : "";

  // Spread ±1σ band
  const upperPoints = hasSeries ? ensembleSeries.map((s, i) => ({ x: getX(i), y: getY(s.mean + s.spreadStd) })) : [];
  const lowerPoints = hasSeries ? ensembleSeries.map((s, i) => ({ x: getX(i), y: getY(Math.max(0, s.mean - s.spreadStd)) })) : [];

  const spreadArea = hasSeries
    ? upperPoints.reduce((acc, p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`), "") +
      lowerPoints
        .slice()
        .reverse()
        .reduce((acc, p) => `${acc} L ${p.x} ${p.y}`, "") +
      " Z"
    : "";

  return (
    <section className="panel bottom-card-panel ensemble-outlook-panel" aria-label="Ensemble Outlook">
      <div className="panel-header">
        <div className="panel-title-group">
          <h2 className="panel-title">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="#4B83C4" strokeWidth="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
            </svg>
            ENSEMBLE OUTLOOK (NCMRWF + TIGGE • {selectedLead})
          </h2>
          <span className="panel-subtitle">Ensemble members and spread</span>
          {state.isDemoMode && (
            <span className="demo-indicator-pill">DEMO SCENARIO</span>
          )}
        </div>

        <select className="select-control compact-select" defaultValue="India (10–30°N, 70–90°E)">
          <option value="India (10–30°N, 70–90°E)">Region: India (10–30°N, 70–90°E)</option>
          <option value="Central India">Central India (Vidarbha/MP)</option>
          <option value="North India">North India Plains</option>
        </select>
      </div>

      <div className="ensemble-chart-container">
        {!hasSeries ? (
          <div className="empty-ensemble-box">
            <div className="empty-ensemble-status-row">
              <span className="status-dot green-dot" />
              <span className="empty-ensemble-headline">11 MEMBERS AVAILABLE — SPATIAL AGGREGATION PENDING</span>
            </div>
            <div className="empty-ensemble-details">
              NCMRWF DEMS Step +24h (m001–m011) perturbation members verified and ingested in local archive.
            </div>
            <div className="empty-ensemble-sub">
              Multi-lead plume dispersion activates once step-aligned temporal verification cases are aggregated.
            </div>
          </div>
        ) : (
          <>
            <svg className="ensemble-svg" viewBox={`0 0 ${width} ${height}`}>
              {/* Y Axis Grid Lines */}
              {[0, 100, 200, 300].map((val) => {
                const y = getY(val);
                return (
                  <g key={val}>
                    <line x1={padL} y1={y} x2={width - padR} y2={y} stroke="rgba(180, 210, 225, 0.08)" strokeWidth="0.8" strokeDasharray="2 3" />
                    <text x={padL - 6} y={y + 3} fill="#6F7C88" fontSize="8" textAnchor="end">{val}</text>
                  </g>
                );
              })}

              {/* Spread ±1σ Envelope */}
              <path d={spreadArea} fill="rgba(75, 131, 196, 0.18)" />

              {/* Individual Ensemble Members (11 curves) */}
              {Array.from({ length: 11 }).map((_, mIdx) => {
                const memberPath = ensembleSeries.reduce((acc, s, i) => {
                  const x = getX(i);
                  const y = getY(s.values[mIdx] || s.mean);
                  return i === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
                }, "");
                return (
                  <path
                    key={mIdx}
                    d={memberPath}
                    fill="none"
                    stroke="#3B82F6"
                    strokeWidth="0.8"
                    opacity="0.38"
                  />
                );
              })}

              {/* Ensemble Mean Line */}
              <path d={meanPath} fill="none" stroke="#F2F5F7" strokeWidth="2" strokeLinecap="round" />
              {ensembleSeries.map((s, i) => (
                <circle key={i} cx={getX(i)} cy={getY(s.mean)} r="2.5" fill="#F2F5F7" stroke="#0B0F14" strokeWidth="1" />
              ))}

              {/* X Axis Labels */}
              {ensembleSeries.map((s, i) => (
                <text key={s.lead} x={getX(i)} y={padT + chartH + 15} fill="#A8B2BD" fontSize="8" textAnchor="middle">
                  {s.lead}
                </text>
              ))}

              {/* Y Axis Label */}
              <text x={10} y={height / 2} fill="#6F7C88" fontSize="7.5" transform={`rotate(-90 10 ${height / 2})`} textAnchor="middle">
                Precipitation (mm)
              </text>
            </svg>

            {/* Legend Overlay on Chart */}
            <div className="ensemble-legend-box">
              <div className="ens-legend-row">
                <span className="ens-line-sample member-line" />
                <span>Ensemble Members</span>
              </div>
              <div className="ens-legend-row">
                <span className="ens-line-sample mean-line" />
                <span>Ensemble Mean</span>
              </div>
              <div className="ens-legend-row">
                <span className="ens-swatch-sample spread-swatch" />
                <span>Spread (±1σ)</span>
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  );
};
