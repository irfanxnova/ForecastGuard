import React, { useState, useMemo } from "react";
import { DashboardState } from "../../types/dashboard";
import { STORMS_CATALOG, VERIFIED_DATASET_RECORDS } from "../../data/casesData";

interface HistoricalAnaloguesViewProps {
  state: DashboardState;
  onNavigateTab: (tab: string) => void;
  onSelectStorm?: (stormName: string) => void;
  onSelectLead?: (lead: string) => void;
}

interface AnalogueMatchResult {
  rank: number;
  caseId: string;
  stormName: string;
  cycleLabel: string;
  leadHours: number;
  leadFormatted: string;
  basin: string;
  similarityScore: number;
  similarityPercent: number;
  distance: number;
  spreadKm: number;
  anisotropyRatio: number;
  bimodalityCoeff: number;
  curvatureDeg: number;
  trackErrorKm: number;
  thresholdKm: number;
  isBust: boolean;
  severity: string;
  quadrant: string;
  forecastLat: number;
  forecastLon: number;
  observedLat: number;
  observedLon: number;
  provenance: string;
}

// Reference population normalization constants from verified 101-record archive
const REF_STATS = {
  spread: { mean: 103.97, std: 29.07, weight: 1.5 },
  anisotropy: { mean: 2.10, std: 0.93, weight: 1.2 },
  bimodality: { mean: 0.21, std: 0.07, weight: 1.0 },
  curvature: { mean: 15.56, std: 25.49, weight: 1.0 },
};
const NORM_SCALE = Math.sqrt(1.5 + 1.2 + 1.0 + 1.0); // ~2.168

export const HistoricalAnaloguesView: React.FC<HistoricalAnaloguesViewProps> = ({
  state,
  onNavigateTab,
  onSelectStorm,
  onSelectLead,
}) => {
  const currentStormName = state.activeStormName || "MIDHILI";
  const [selectedLeadHours, setSelectedLeadHours] = useState<number>(() => {
    const match = state.selectedLead.match(/\d+/);
    return match ? parseInt(match[0], 10) : 24;
  });
  const [selectedMatchId, setSelectedMatchId] = useState<string | null>(null);
  const [excludeSameStorm, setExcludeSameStorm] = useState<boolean>(true);

  // Locate the active query record in verified dataset
  const queryRecord = useMemo(() => {
    return VERIFIED_DATASET_RECORDS.find(
      (r) =>
        r.storm_name.toUpperCase() === currentStormName.toUpperCase() &&
        r.forecast_lead_hours === selectedLeadHours
    ) || VERIFIED_DATASET_RECORDS.find(
      (r) => r.storm_name.toUpperCase() === currentStormName.toUpperCase()
    ) || VERIFIED_DATASET_RECORDS[0];
  }, [currentStormName, selectedLeadHours]);

  // Compute deterministic standardized Euclidean distances to all candidates
  const rankedMatches = useMemo<AnalogueMatchResult[]>(() => {
    if (!queryRecord) return [];

    const qSpread = queryRecord.ensemble_spread_km;
    const qAniso = queryRecord.anisotropy_ratio || 1.5;
    const qBimod = queryRecord.bimodality_coefficient || 0.2;
    const qCurv = queryRecord.trajectory_curvature_deg || 10.0;

    const candidates = VERIFIED_DATASET_RECORDS.filter((r) => {
      // Exclude exact same synoptic fix
      if (
        r.storm_name === queryRecord.storm_name &&
        r.cycle_label === queryRecord.cycle_label &&
        r.forecast_lead_hours === queryRecord.forecast_lead_hours
      ) {
        return false;
      }
      if (excludeSameStorm && r.storm_name === queryRecord.storm_name) {
        return false;
      }
      return true;
    });

    const scored = candidates.map((cand) => {
      const cSpread = cand.ensemble_spread_km;
      const cAniso = cand.anisotropy_ratio || 1.5;
      const cBimod = cand.bimodality_coefficient || 0.2;
      const cCurv = cand.trajectory_curvature_deg || 10.0;

      const dzSpread = (cSpread - qSpread) / REF_STATS.spread.std;
      const dzAniso = (cAniso - qAniso) / REF_STATS.anisotropy.std;
      const dzBimod = (cBimod - qBimod) / REF_STATS.bimodality.std;
      const dzCurv = (cCurv - qCurv) / REF_STATS.curvature.std;

      const distSq =
        REF_STATS.spread.weight * dzSpread * dzSpread +
        REF_STATS.anisotropy.weight * dzAniso * dzAniso +
        REF_STATS.bimodality.weight * dzBimod * dzBimod +
        REF_STATS.curvature.weight * dzCurv * dzCurv;

      const distance = Math.sqrt(distSq);
      const similarity = 1.0 / (1.0 + distance / NORM_SCALE);
      const simPercent = Math.round(similarity * 100);

      const caseId = `2023_${cand.storm_name}_${cand.cycle_label}_plus${String(cand.forecast_lead_hours).padStart(2, "0")}h`;

      return {
        rank: 0,
        caseId,
        stormName: cand.storm_name,
        cycleLabel: cand.cycle_label,
        leadHours: cand.forecast_lead_hours,
        leadFormatted: `+${String(cand.forecast_lead_hours).padStart(2, "0")}h`,
        basin: cand.basin,
        similarityScore: similarity,
        similarityPercent: simPercent,
        distance,
        spreadKm: cand.ensemble_spread_km,
        anisotropyRatio: cand.anisotropy_ratio || 1.0,
        bimodalityCoeff: cand.bimodality_coefficient || 0.0,
        curvatureDeg: cand.trajectory_curvature_deg || 0.0,
        trackErrorKm: cand.track_error_km,
        thresholdKm: cand.threshold_km,
        isBust: cand.bust_label === 1,
        severity: cand.severity || "NORMAL",
        quadrant: cand.confidence_quadrant || "UNKNOWN",
        forecastLat: cand.forecast_lat,
        forecastLon: cand.forecast_lon,
        observedLat: cand.observed_lat,
        observedLon: cand.observed_lon,
        provenance: cand.provenance || "NCMRWF NEPS vs Official IMD/RSMC Best Track",
      };
    });

    // Sort ascending by distance (closest first)
    scored.sort((a, b) => a.distance - b.distance);

    return scored.slice(0, 8).map((m, idx) => ({
      ...m,
      rank: idx + 1,
    }));
  }, [queryRecord, excludeSameStorm]);

  // Selected HALO analogue
  const activeHaloMatch = useMemo(() => {
    if (!rankedMatches.length) return null;
    if (!selectedMatchId) return rankedMatches[0];
    return rankedMatches.find((m) => m.caseId === selectedMatchId) || rankedMatches[0];
  }, [rankedMatches, selectedMatchId]);

  const handleInspectAnalogue = (stormName: string, leadFormatted: string) => {
    if (onSelectStorm) {
      onSelectStorm(stormName);
    }
    if (onSelectLead) {
      onSelectLead(leadFormatted);
    }
    onNavigateTab("dashboard");
  };

  const leadOptions = [6, 12, 18, 24, 30, 36, 42, 48];

  return (
    <div className="sub-view-panel panel" style={{ width: "100%", padding: "20px" }}>
      {/* Header */}
      <div className="panel-header" style={{ marginBottom: "16px" }}>
        <div className="panel-title-group">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span
              style={{
                background: "rgba(245, 184, 61, 0.15)",
                color: "#F5B83D",
                border: "1px solid rgba(245, 184, 61, 0.3)",
                padding: "2px 6px",
                borderRadius: "3px",
                fontSize: "10px",
                fontWeight: 700,
                letterSpacing: "0.5px",
              }}
            >
              ECHO MEMORY
            </span>
            <h2 className="panel-title" style={{ fontSize: "16px", color: "#F5B83D" }}>
              HISTORICAL FORECAST MEMORY &amp; BUST ATLAS
            </h2>
          </div>
          <span className="panel-subtitle">
            Deterministic synoptic forecast-state matching across 101 verified North Indian Ocean leads
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

      {/* Mandatory Scientific Non-Causal Guard */}
      <div
        style={{
          background: "rgba(245, 184, 61, 0.08)",
          borderLeft: "3px solid #F5B83D",
          padding: "10px 14px",
          borderRadius: "0 4px 4px 0",
          marginBottom: "18px",
          fontSize: "11.5px",
          lineHeight: 1.45,
          color: "#E2E8F0",
        }}
      >
        <strong style={{ color: "#FFD36A" }}>ECHO / GHOST (HISTORICAL MEMORY ONLY):</strong> Matching identifies prior forecast states with similar measured ensemble dispersion and trajectory geometry. <em>Historical similarity does NOT assert physical causation and does NOT guarantee identical future atmospheric evolution.</em> Verified historical outcomes are attached strictly post-retrieval from authoritative IMD/RSMC best-track archives.
      </div>

      {/* Query Control Bar: Current Forecast State */}
      <div
        className="metric-card"
        style={{
          padding: "16px",
          marginBottom: "20px",
          border: "1px solid rgba(245, 184, 61, 0.4)",
          background: "rgba(10, 16, 24, 0.85)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px" }}>
          <div>
            <div style={{ fontSize: "10px", color: "#F5B83D", fontWeight: 700, letterSpacing: "0.5px", textTransform: "uppercase" }}>
              CURRENT FORECAST STATE (AT CUTOFF T)
            </div>
            <div style={{ fontSize: "18px", fontWeight: 800, color: "#FFFFFF", marginTop: "4px" }}>
              CYCLONE {currentStormName} · +{String(selectedLeadHours).padStart(2, "0")}h SYNOPTIC LEAD
            </div>
            <div style={{ fontSize: "11px", color: "#A8B2BD", marginTop: "2px" }}>
              Cycle: {queryRecord?.cycle_label || "00Z"} · Basin: {queryRecord?.basin || "North Indian Ocean"}
            </div>
          </div>

          {/* Controls */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "11px", color: "#A8B2BD" }}>Investigate Storm:</span>
              <select
                value={currentStormName}
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

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "11px", color: "#A8B2BD" }}>Lead:</span>
              <select
                value={selectedLeadHours}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  setSelectedLeadHours(val);
                  if (onSelectLead) onSelectLead(`+${String(val).padStart(2, "0")}h`);
                }}
                className="select-control"
                style={{ padding: "4px 8px", fontSize: "11px", fontWeight: 600 }}
              >
                {leadOptions.map((l) => (
                  <option key={l} value={l}>
                    +{String(l).padStart(2, "0")}h
                  </option>
                ))}
              </select>
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", color: "#C5D0DC", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={excludeSameStorm}
                onChange={(e) => setExcludeSameStorm(e.target.checked)}
              />
              Exclude same storm
            </label>
          </div>
        </div>

        {/* Query Measured Predictor Features */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "10px", marginTop: "14px", paddingTop: "12px", borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
          <div>
            <div style={{ fontSize: "10px", color: "#8E9DAE" }}>ENSEMBLE SPREAD</div>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "#FFFFFF" }}>{queryRecord?.ensemble_spread_km.toFixed(1)} km</div>
          </div>
          <div>
            <div style={{ fontSize: "10px", color: "#8E9DAE" }}>ANISOTROPY RATIO</div>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "#FFFFFF" }}>{queryRecord?.anisotropy_ratio?.toFixed(2) || "1.50"}</div>
          </div>
          <div>
            <div style={{ fontSize: "10px", color: "#8E9DAE" }}>BIMODALITY COEFF</div>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "#FFFFFF" }}>{queryRecord?.bimodality_coefficient?.toFixed(3) || "0.200"}</div>
          </div>
          <div>
            <div style={{ fontSize: "10px", color: "#8E9DAE" }}>TRAJECTORY TURNING</div>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "#FFFFFF" }}>{queryRecord?.trajectory_curvature_deg?.toFixed(1) || "0.0"}°</div>
          </div>
          <div>
            <div style={{ fontSize: "10px", color: "#8E9DAE" }}>FORECAST VORTEX</div>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "#45B7D1" }}>
              {queryRecord?.forecast_lat.toFixed(1)}°N, {queryRecord?.forecast_lon.toFixed(1)}°E
            </div>
          </div>
        </div>
      </div>

      {/* Main Two-Column View: Ranked Analogue Cards (Left) + Selected HALO Deep Evidence (Right) */}
      <div style={{ display: "grid", gridTemplateColumns: "minmax(340px, 1fr) minmax(360px, 1.1fr)", gap: "20px" }}>
        {/* Left Column: Ranked Matches */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <h3 style={{ fontSize: "13px", color: "#FFFFFF", margin: 0 }}>
              CLOSEST HISTORICAL ANALOGUES ({rankedMatches.length} MATCHES)
            </h3>
            <span style={{ fontSize: "10.5px", color: "#8E9DAE" }}>
              Standardized Euclidean Metric
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {rankedMatches.map((m) => {
              const isSelected = activeHaloMatch?.caseId === m.caseId;
              return (
                <div
                  key={m.caseId}
                  className="metric-card"
                  onClick={() => setSelectedMatchId(m.caseId)}
                  style={{
                    padding: "14px",
                    cursor: "pointer",
                    border: isSelected ? "2px solid #F5B83D" : "1px solid rgba(255, 255, 255, 0.08)",
                    boxShadow: isSelected ? "0 0 14px rgba(245, 184, 61, 0.25)" : "none",
                    background: isSelected ? "rgba(245, 184, 61, 0.05)" : "rgba(10, 16, 24, 0.7)",
                    transition: "all 0.2s ease",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span
                        style={{
                          background: isSelected ? "#F5B83D" : "rgba(255, 255, 255, 0.1)",
                          color: isSelected ? "#0A1018" : "#FFFFFF",
                          fontWeight: 800,
                          fontSize: "10.5px",
                          padding: "1px 6px",
                          borderRadius: "3px",
                        }}
                      >
                        #{m.rank}
                      </span>
                      <span style={{ fontSize: "14px", fontWeight: 800, color: "#FFFFFF" }}>
                        {m.stormName} ({m.leadFormatted})
                      </span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span
                        className="badge"
                        style={{
                          background: m.similarityPercent >= 60 ? "rgba(85, 217, 138, 0.18)" : "rgba(69, 183, 209, 0.18)",
                          color: m.similarityPercent >= 60 ? "#55D98A" : "#45B7D1",
                          borderColor: m.similarityPercent >= 60 ? "rgba(85, 217, 138, 0.4)" : "rgba(69, 183, 209, 0.4)",
                          fontSize: "10.5px",
                          fontWeight: 700,
                        }}
                      >
                        {m.similarityPercent}% Match
                      </span>
                    </div>
                  </div>

                  <div style={{ fontSize: "11px", color: "#8E9DAE", marginBottom: "8px" }}>
                    {m.cycleLabel} · {m.basin} · Distance d = {m.distance.toFixed(2)}
                  </div>

                  {/* Feature Echo Strip */}
                  <div style={{ display: "flex", gap: "10px", fontSize: "11px", color: "#C5D0DC", marginBottom: "10px" }}>
                    <span>Spread: <strong>{m.spreadKm.toFixed(0)} km</strong></span>
                    <span>Aniso: <strong>{m.anisotropyRatio.toFixed(2)}</strong></span>
                    <span>Bimod: <strong>{m.bimodalityCoeff.toFixed(3)}</strong></span>
                  </div>

                  {/* TRACE: Verified Historical Outcome Badge */}
                  <div
                    style={{
                      background: m.isBust ? "rgba(239, 68, 68, 0.12)" : "rgba(85, 217, 138, 0.1)",
                      border: `1px solid ${m.isBust ? "rgba(239, 68, 68, 0.3)" : "rgba(85, 217, 138, 0.25)"}`,
                      padding: "6px 10px",
                      borderRadius: "4px",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      fontSize: "11px",
                    }}
                  >
                    <span style={{ color: m.isBust ? "#FF7878" : "#55D98A", fontWeight: 700 }}>
                      TRACE: {m.isBust ? "VERIFIED BUST" : "VERIFIED NOMINAL"}
                    </span>
                    <span style={{ color: "#E2E8F0" }}>
                      Error: <strong>{m.trackErrorKm.toFixed(1)} km</strong> (tau={m.thresholdKm.toFixed(1)} km)
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: HALO Detailed Analogue Investigation */}
        <div>
          {activeHaloMatch ? (
            <div
              className="metric-card"
              style={{
                padding: "20px",
                border: "2px solid #F5B83D",
                background: "rgba(10, 16, 24, 0.9)",
                boxShadow: "0 0 20px rgba(245, 184, 61, 0.2)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "14px" }}>
                <div>
                  <span
                    style={{
                      background: "rgba(245, 184, 61, 0.2)",
                      color: "#FFD36A",
                      fontSize: "10px",
                      fontWeight: 800,
                      padding: "2px 6px",
                      borderRadius: "3px",
                      letterSpacing: "0.5px",
                    }}
                  >
                    HALO SELECTED ANALOGUE
                  </span>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "#FFFFFF", marginTop: "4px" }}>
                    CYCLONE {activeHaloMatch.stormName} ({activeHaloMatch.leadFormatted})
                  </div>
                  <div style={{ fontSize: "11px", color: "#A8B2BD" }}>
                    Cycle: {activeHaloMatch.cycleLabel} · Basin: {activeHaloMatch.basin}
                  </div>
                </div>

                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "22px", fontWeight: 800, color: "#F5B83D" }}>
                    {activeHaloMatch.similarityPercent}%
                  </div>
                  <div style={{ fontSize: "10.5px", color: "#8E9DAE" }}>
                    Distance d = {activeHaloMatch.distance.toFixed(2)}
                  </div>
                </div>
              </div>

              {/* What Actually Happened (Ground Truth Verified Outcome) */}
              <div
                style={{
                  background: activeHaloMatch.isBust ? "rgba(239, 68, 68, 0.1)" : "rgba(85, 217, 138, 0.08)",
                  border: `1px solid ${activeHaloMatch.isBust ? "rgba(239, 68, 68, 0.3)" : "rgba(85, 217, 138, 0.3)"}`,
                  borderRadius: "6px",
                  padding: "12px 14px",
                  marginBottom: "16px",
                }}
              >
                <div style={{ fontSize: "10.5px", color: activeHaloMatch.isBust ? "#FF7878" : "#55D98A", fontWeight: 800, letterSpacing: "0.5px" }}>
                  WHAT ACTUALLY HAPPENED (GROUND TRUTH VERIFICATION)
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "6px" }}>
                  <div>
                    <span style={{ fontSize: "16px", fontWeight: 800, color: "#FFFFFF" }}>
                      Track Error: {activeHaloMatch.trackErrorKm.toFixed(1)} km
                    </span>
                    <span style={{ fontSize: "11px", color: "#8E9DAE", marginLeft: "8px" }}>
                      Tolerance Threshold &tau; = {activeHaloMatch.thresholdKm.toFixed(1)} km
                    </span>
                  </div>
                  <span
                    className="badge"
                    style={{
                      background: activeHaloMatch.isBust ? "rgba(239, 68, 68, 0.25)" : "rgba(85, 217, 138, 0.25)",
                      color: activeHaloMatch.isBust ? "#FF7878" : "#55D98A",
                      fontWeight: 800,
                      fontSize: "11px",
                    }}
                  >
                    {activeHaloMatch.isBust ? `BUST (${activeHaloMatch.severity})` : "NOMINAL"}
                  </span>
                </div>

                <div style={{ fontSize: "11px", color: "#C5D0DC", marginTop: "8px", lineHeight: 1.4 }}>
                  Forecast Position: {activeHaloMatch.forecastLat.toFixed(2)}°N, {activeHaloMatch.forecastLon.toFixed(2)}°E<br />
                  Observed RSMC Position: {activeHaloMatch.observedLat.toFixed(2)}°N, {activeHaloMatch.observedLon.toFixed(2)}°E
                </div>
              </div>

              {/* Dimension Breakdown Comparison */}
              <h4 style={{ fontSize: "11.5px", color: "#FFFFFF", marginBottom: "8px" }}>
                PREDICTOR FEATURE COMPARISON (AT CUTOFF T)
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "16px", fontSize: "11px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "110px 1fr 1fr", color: "#8E9DAE", borderBottom: "1px solid rgba(255, 255, 255, 0.08)", paddingBottom: "4px" }}>
                  <span>DIMENSION</span>
                  <span>CURRENT STATE</span>
                  <span>HISTORICAL ANALOGUE</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "110px 1fr 1fr", color: "#E2E8F0" }}>
                  <span style={{ color: "#A8B2BD" }}>Spread</span>
                  <span>{queryRecord?.ensemble_spread_km.toFixed(1)} km</span>
                  <span style={{ color: "#FFD36A", fontWeight: 700 }}>{activeHaloMatch.spreadKm.toFixed(1)} km</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "110px 1fr 1fr", color: "#E2E8F0" }}>
                  <span style={{ color: "#A8B2BD" }}>Anisotropy</span>
                  <span>{queryRecord?.anisotropy_ratio?.toFixed(2) || "1.50"}</span>
                  <span style={{ color: "#FFD36A", fontWeight: 700 }}>{activeHaloMatch.anisotropyRatio.toFixed(2)}</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "110px 1fr 1fr", color: "#E2E8F0" }}>
                  <span style={{ color: "#A8B2BD" }}>Bimodality</span>
                  <span>{queryRecord?.bimodality_coefficient?.toFixed(3) || "0.200"}</span>
                  <span style={{ color: "#FFD36A", fontWeight: 700 }}>{activeHaloMatch.bimodalityCoeff.toFixed(3)}</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "110px 1fr 1fr", color: "#E2E8F0" }}>
                  <span style={{ color: "#A8B2BD" }}>Curvature</span>
                  <span>{queryRecord?.trajectory_curvature_deg?.toFixed(1) || "0.0"}°</span>
                  <span style={{ color: "#FFD36A", fontWeight: 700 }}>{activeHaloMatch.curvatureDeg.toFixed(1)}°</span>
                </div>
              </div>

              {/* THREAD: Provenance & Audit Verification */}
              <div
                style={{
                  background: "rgba(10, 16, 24, 0.8)",
                  padding: "10px 12px",
                  borderRadius: "4px",
                  fontSize: "10.5px",
                  color: "#8E9DAE",
                  marginBottom: "16px",
                  border: "1px solid rgba(255, 255, 255, 0.05)",
                }}
              >
                <div style={{ fontWeight: 700, color: "#C5D0DC", marginBottom: "3px" }}>
                  THREAD: VERIFICATION PROVENANCE
                </div>
                <div>{activeHaloMatch.provenance}</div>
                <div style={{ marginTop: "2px" }}>Case ID: {activeHaloMatch.caseId}</div>
              </div>

              {/* Action Button */}
              <button
                className="investigate-btn"
                style={{
                  width: "100%",
                  justifyContent: "center",
                  fontSize: "11.5px",
                  background: "rgba(245, 184, 61, 0.15)",
                  color: "#F5B83D",
                  border: "1px solid #F5B83D",
                  padding: "8px 12px",
                }}
                onClick={() => handleInspectAnalogue(activeHaloMatch.stormName, activeHaloMatch.leadFormatted)}
              >
                Load {activeHaloMatch.stormName} ({activeHaloMatch.leadFormatted}) into Workspace →
              </button>
            </div>
          ) : (
            <div className="metric-card" style={{ padding: "20px", textAlign: "center", color: "#8E9DAE" }}>
              No historical analogues match the selected criteria.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
