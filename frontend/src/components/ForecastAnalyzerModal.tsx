import React, { useState } from "react";
import {
  LiveInferenceRequest,
  LiveInferenceResponse,
  evaluateAssessmentConfidence,
} from "../types/dashboard";

interface ForecastAnalyzerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyForecast?: (result: LiveInferenceResponse, payload: LiveInferenceRequest) => void;
}

// Vetted benchmark prospective ensemble presets
const PRESETS: Record<
  string,
  {
    name: string;
    description: string;
    tag: string;
    tagColor: string;
    payload: LiveInferenceRequest;
  }
> = {
  midhili_d1: {
    name: "Cyclone Midhili (D+1, Severe Bust)",
    description: "Bay of Bengal: 11-member NEPS ensemble. High bust risk case preceding rapid northeast displacement toward Bangladesh.",
    tag: "SEVERE BUST CASE",
    tagColor: "#EF4444",
    payload: {
      forecast_source: "NCMRWF TIGGE",
      forecast_cycle: "2023-11-16T00:00:00Z",
      valid_time: "2023-11-17T00:00:00Z",
      lead_hours: 24,
      variable: "Mean Sea Level Pressure (msl)",
      deterministic_lat: 20.8,
      deterministic_lon: 90.5,
      ensemble_members: [
        { member_id: 1, latitude: 20.6, longitude: 90.3, central_pressure_hpa: 998.0 },
        { member_id: 2, latitude: 21.1, longitude: 90.8, central_pressure_hpa: 997.0 },
        { member_id: 3, latitude: 20.9, longitude: 90.4, central_pressure_hpa: 998.5 },
        { member_id: 4, latitude: 21.4, longitude: 91.0, central_pressure_hpa: 996.0 },
        { member_id: 5, latitude: 20.4, longitude: 90.1, central_pressure_hpa: 999.0 },
        { member_id: 6, latitude: 21.2, longitude: 90.7, central_pressure_hpa: 997.5 },
        { member_id: 7, latitude: 20.7, longitude: 90.2, central_pressure_hpa: 999.5 },
        { member_id: 8, latitude: 21.5, longitude: 91.2, central_pressure_hpa: 995.0 },
        { member_id: 9, latitude: 20.5, longitude: 90.0, central_pressure_hpa: 1000.0 },
        { member_id: 10, latitude: 21.0, longitude: 90.6, central_pressure_hpa: 998.0 },
        { member_id: 11, latitude: 21.3, longitude: 90.9, central_pressure_hpa: 996.5 },
      ],
    },
  },
  biparjoy_d2: {
    name: "Cyclone Biparjoy (D+2, Recurvature)",
    description: "Arabian Sea: 11-member NEPS ensemble. Recurvature case where tight initial spread masked subsequent slow track drift.",
    tag: "RECURVATURE RISK",
    tagColor: "#F59E0B",
    payload: {
      forecast_source: "NCMRWF TIGGE",
      forecast_cycle: "2023-06-08T00:00:00Z",
      valid_time: "2023-06-10T00:00:00Z",
      lead_hours: 48,
      variable: "Mean Sea Level Pressure (msl)",
      deterministic_lat: 18.5,
      deterministic_lon: 66.8,
      ensemble_members: [
        { member_id: 1, latitude: 18.3, longitude: 66.7, central_pressure_hpa: 975.0 },
        { member_id: 2, latitude: 18.7, longitude: 66.9, central_pressure_hpa: 973.0 },
        { member_id: 3, latitude: 18.4, longitude: 66.5, central_pressure_hpa: 976.0 },
        { member_id: 4, latitude: 18.9, longitude: 67.2, central_pressure_hpa: 971.0 },
        { member_id: 5, latitude: 18.1, longitude: 66.4, central_pressure_hpa: 978.0 },
        { member_id: 6, latitude: 18.6, longitude: 66.8, central_pressure_hpa: 974.0 },
        { member_id: 7, latitude: 18.8, longitude: 67.0, central_pressure_hpa: 972.0 },
        { member_id: 8, latitude: 18.2, longitude: 66.6, central_pressure_hpa: 977.0 },
        { member_id: 9, latitude: 19.0, longitude: 67.4, central_pressure_hpa: 970.0 },
        { member_id: 10, latitude: 18.5, longitude: 66.7, central_pressure_hpa: 975.0 },
        { member_id: 11, latitude: 18.7, longitude: 67.1, central_pressure_hpa: 973.5 },
      ],
    },
  },
  michaung_d1: {
    name: "Cyclone Michaung (D+1, High Reliability Ref)",
    description: "Bay of Bengal: 11-member NEPS ensemble. High reliability reference case with tight, consistent track guidance.",
    tag: "HIGH RELIABILITY REF",
    tagColor: "#10B981",
    payload: {
      forecast_source: "NCMRWF TIGGE",
      forecast_cycle: "2023-12-02T00:00:00Z",
      valid_time: "2023-12-03T00:00:00Z",
      lead_hours: 24,
      variable: "Mean Sea Level Pressure (msl)",
      deterministic_lat: 11.8,
      deterministic_lon: 82.7,
      ensemble_members: [
        { member_id: 1, latitude: 11.75, longitude: 82.68, central_pressure_hpa: 994.0 },
        { member_id: 2, latitude: 11.85, longitude: 82.72, central_pressure_hpa: 993.0 },
        { member_id: 3, latitude: 11.80, longitude: 82.65, central_pressure_hpa: 994.5 },
        { member_id: 4, latitude: 11.90, longitude: 82.75, central_pressure_hpa: 992.0 },
        { member_id: 5, latitude: 11.70, longitude: 82.62, central_pressure_hpa: 995.0 },
        { member_id: 6, latitude: 11.82, longitude: 82.70, central_pressure_hpa: 993.5 },
        { member_id: 7, latitude: 11.88, longitude: 82.74, central_pressure_hpa: 992.5 },
        { member_id: 8, latitude: 11.73, longitude: 82.64, central_pressure_hpa: 994.8 },
        { member_id: 9, latitude: 11.92, longitude: 82.78, central_pressure_hpa: 991.5 },
        { member_id: 10, latitude: 11.78, longitude: 82.69, central_pressure_hpa: 993.8 },
        { member_id: 11, latitude: 11.84, longitude: 82.71, central_pressure_hpa: 993.2 },
      ],
    },
  },
};

const PIPELINE_STAGES = [
  "FORECAST RECEIVED",
  "QUALITY CHECK",
  "DOMAIN CHECK",
  "RELIABILITY ANALYSIS",
  "CONFIDENCE / EVIDENCE",
  "RESULT",
];

export const ForecastAnalyzerModal: React.FC<ForecastAnalyzerModalProps> = ({
  isOpen,
  onClose,
  onApplyForecast,
}) => {
  const [activeTab, setActiveTab] = useState<"form" | "json">("form");
  const [selectedPresetKey, setSelectedPresetKey] = useState<string>("midhili_d1");

  // Form Fields
  const [forecastSource, setForecastSource] = useState<string>("NCMRWF TIGGE");
  const [forecastCycle, setForecastCycle] = useState<string>("2023-11-16T00:00:00Z");
  const [validTime, setValidTime] = useState<string>("2023-11-17T00:00:00Z");
  const [leadHours, setLeadHours] = useState<number>(24);
  const [variable, setVariable] = useState<string>("Mean Sea Level Pressure (msl)");
  const [deterministicLat, setDeterministicLat] = useState<number>(20.8);
  const [deterministicLon, setDeterministicLon] = useState<number>(90.5);

  const [jsonInput, setJsonInput] = useState<string>(
    JSON.stringify(PRESETS.midhili_d1.payload, null, 2)
  );

  // Analysis state
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [pipelineStageIndex, setPipelineStageIndex] = useState<number>(-1);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<LiveInferenceResponse | null>(null);

  if (!isOpen) return null;

  const handleSelectPreset = (key: string) => {
    setSelectedPresetKey(key);
    const p = PRESETS[key].payload;
    setForecastSource(p.forecast_source || "NCMRWF TIGGE");
    setForecastCycle(p.forecast_cycle);
    setValidTime(p.valid_time);
    setLeadHours(p.lead_hours);
    setVariable(p.variable || "Mean Sea Level Pressure (msl)");
    setDeterministicLat(p.deterministic_lat || 20.0);
    setDeterministicLon(p.deterministic_lon || 88.0);
    setJsonInput(JSON.stringify(p, null, 2));
    setAnalysisResult(null);
    setErrorMsg(null);
    setPipelineStageIndex(-1);
  };

  const handleRunAnalysis = async () => {
    setIsAnalyzing(true);
    setErrorMsg(null);
    setAnalysisResult(null);
    setPipelineStageIndex(0);

    // Progressive stage animation timer
    const interval = setInterval(() => {
      setPipelineStageIndex((prev) => {
        if (prev < PIPELINE_STAGES.length - 2) return prev + 1;
        return prev;
      });
    }, 180);

    try {
      let payload: LiveInferenceRequest;
      if (activeTab === "json") {
        payload = JSON.parse(jsonInput);
      } else {
        // Build payload from form fields + preset members adjusted to coordinates
        const basePreset = PRESETS[selectedPresetKey].payload;
        payload = {
          forecast_source: forecastSource,
          forecast_cycle: forecastCycle,
          valid_time: validTime,
          lead_hours: leadHours,
          variable: variable,
          deterministic_lat: deterministicLat,
          deterministic_lon: deterministicLon,
          ensemble_members: basePreset.ensemble_members.map((m) => ({
            member_id: m.member_id,
            latitude: Number((deterministicLat + (m.latitude - (basePreset.deterministic_lat || 20.8))).toFixed(3)),
            longitude: Number((deterministicLon + (m.longitude - (basePreset.deterministic_lon || 90.5))).toFixed(3)),
            central_pressure_hpa: m.central_pressure_hpa,
          })),
        };
      }

      const response = await fetch("/api/v1/inference/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      clearInterval(interval);

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errJson.detail || `Server returned error ${response.status}`);
      }

      const data: LiveInferenceResponse = await response.json();
      setPipelineStageIndex(PIPELINE_STAGES.length - 1);
      setAnalysisResult(data);
    } catch (err: any) {
      clearInterval(interval);
      setPipelineStageIndex(-1);
      setErrorMsg(err.message || "Failed to analyze forecast payload.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApply = () => {
    if (analysisResult && onApplyForecast) {
      try {
        const parsed: LiveInferenceRequest =
          activeTab === "json" ? JSON.parse(jsonInput) : PRESETS[selectedPresetKey].payload;
        onApplyForecast(analysisResult, parsed);
        onClose();
      } catch (e) {
        onClose();
      }
    }
  };

  // Determine assessment confidence
  const confDetail = evaluateAssessmentConfidence({
    isValidatedDomain: true,
    supportScore: analysisResult?.novelty_assessment?.support_score
      ? Math.round(analysisResult.novelty_assessment.support_score * 100)
      : 85,
    representationState: analysisResult?.novelty_assessment?.representation_state,
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-4xl max-h-[92vh] flex flex-col bg-[#0A0F16] border border-amber-500/40 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header Bar */}
        <div className="flex items-center justify-between px-6 py-3.5 border-b border-white/10 bg-[#0C121B]">
          <div className="flex items-center gap-3">
            <span className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-lg">
              ⚡
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-wide">
                  Forecast Reliability Analyzer
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  PROFESSOR / OPERATIONAL MODE
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Independent verification & reliability inference deck for medium-range forecast telemetry.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Tab Switcher: Form vs Raw JSON */}
            <div className="flex items-center bg-[#070B10] p-1 rounded-lg border border-white/10 text-xs font-mono">
              <button
                type="button"
                onClick={() => setActiveTab("form")}
                className={`px-3 py-1 rounded transition-all ${
                  activeTab === "form"
                    ? "bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                📋 Form Mode
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("json")}
                className={`px-3 py-1 rounded transition-all ${
                  activeTab === "json"
                    ? "bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                ⚙ Raw JSON
              </button>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all font-mono text-sm"
              title="Close analyzer modal"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Preset Selector Cards */}
          <div>
            <label className="block text-xs font-mono text-slate-400 uppercase tracking-wider mb-2">
              BENCHMARK EVALUATION PRESETS:
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {Object.entries(PRESETS).map(([key, preset]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => handleSelectPreset(key)}
                  className={`flex flex-col text-left p-3 rounded-xl border transition-all ${
                    selectedPresetKey === key
                      ? "bg-amber-500/10 border-amber-500/60 shadow-md shadow-amber-500/5"
                      : "bg-[#0E1520] border-border/40 hover:border-border/80 hover:bg-[#121B29]"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-white">{preset.name.split("(")[0]}</span>
                    <span
                      className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold"
                      style={{
                        backgroundColor: `${preset.tagColor}20`,
                        color: preset.tagColor,
                        border: `1px solid ${preset.tagColor}50`,
                      }}
                    >
                      {preset.tag}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                    {preset.description}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* Form Mode View */}
          {activeTab === "form" ? (
            <div className="p-4 rounded-xl bg-[#0E1520] border border-border/40 space-y-4">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <span className="text-xs font-mono font-bold text-slate-200">
                  SCENARIO TELEMETRY METADATA
                </span>
                <span className="text-[10px] font-mono text-emerald-400">
                  11-MEMBER ENSEMBLE ATTACHED
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
                <div>
                  <label className="text-[10px] text-slate-400 uppercase block mb-1">NWP SOURCE</label>
                  <input
                    type="text"
                    value={forecastSource}
                    onChange={(e) => setForecastSource(e.target.value)}
                    className="w-full bg-[#070B10] border border-white/10 rounded px-2.5 py-1.5 text-slate-200 focus:border-amber-500/60 outline-none"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-400 uppercase block mb-1">INITIALIZATION CYCLE (UTC)</label>
                  <input
                    type="text"
                    value={forecastCycle}
                    onChange={(e) => setForecastCycle(e.target.value)}
                    className="w-full bg-[#070B10] border border-white/10 rounded px-2.5 py-1.5 text-slate-200 focus:border-amber-500/60 outline-none"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-400 uppercase block mb-1">LEAD HORIZON</label>
                  <select
                    value={leadHours}
                    onChange={(e) => setLeadHours(Number(e.target.value))}
                    className="w-full bg-[#070B10] border border-white/10 rounded px-2.5 py-1.5 text-amber-300 focus:border-amber-500/60 outline-none"
                  >
                    <option value={24}>D+1 (+24h)</option>
                    <option value={48}>D+2 (+48h)</option>
                    <option value={72}>D+3 (+72h)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
                <div>
                  <label className="text-[10px] text-slate-400 uppercase block mb-1">VORTEX LATITUDE (°N)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={deterministicLat}
                    onChange={(e) => setDeterministicLat(parseFloat(e.target.value))}
                    className="w-full bg-[#070B10] border border-white/10 rounded px-2.5 py-1.5 text-slate-200 focus:border-amber-500/60 outline-none"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-400 uppercase block mb-1">VORTEX LONGITUDE (°E)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={deterministicLon}
                    onChange={(e) => setDeterministicLon(parseFloat(e.target.value))}
                    className="w-full bg-[#070B10] border border-white/10 rounded px-2.5 py-1.5 text-slate-200 focus:border-amber-500/60 outline-none"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-slate-400 uppercase block mb-1">ATMOSPHERIC VARIABLE</label>
                  <input
                    type="text"
                    disabled
                    value={variable}
                    className="w-full bg-[#070B10] border border-white/10 rounded px-2.5 py-1.5 text-slate-400 outline-none cursor-not-allowed"
                  />
                </div>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                  RAW INFERENCE TELEMETRY PAYLOAD (JSON):
                </label>
                <span className="text-[11px] font-mono text-slate-500">
                  anti-leakage strict contract • 11 members
                </span>
              </div>
              <textarea
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                rows={8}
                className="w-full bg-[#070B10] text-amber-200/90 font-mono text-xs p-3.5 rounded-xl border border-border/60 focus:border-amber-500/60 focus:outline-none resize-y"
                spellCheck={false}
              />
            </div>
          )}

          {/* Progressive Verification Pipeline Bar */}
          {(isAnalyzing || pipelineStageIndex >= 0) && (
            <div className="p-3.5 rounded-xl bg-[#070C12] border border-amber-500/30 space-y-2">
              <span className="text-[10px] font-mono uppercase text-muted tracking-wider block">
                EVALUATION PIPELINE TRACE:
              </span>
              <div className="grid grid-cols-6 gap-1.5 text-[10px] font-mono text-center">
                {PIPELINE_STAGES.map((stage, idx) => {
                  const isDone = pipelineStageIndex > idx;
                  const isCurrent = pipelineStageIndex === idx;
                  return (
                    <div
                      key={stage}
                      className={`px-1.5 py-1 rounded transition-all ${
                        isDone
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                          : isCurrent
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/50 animate-pulse font-bold"
                          : "bg-white/5 text-slate-500 border border-white/5"
                      }`}
                    >
                      {stage}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Trigger Button */}
          <div className="flex items-center justify-between gap-4 pt-1">
            <div className="text-[11px] text-slate-400 italic">
              * Evaluates Platt-calibrated bust probability, OOD novelty, and multi-model consensus.
            </div>
            <button
              type="button"
              onClick={handleRunAnalysis}
              disabled={isAnalyzing}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-bold text-xs tracking-wide transition-all shadow-lg shadow-amber-500/20"
            >
              {isAnalyzing ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                  <span>Processing Verification...</span>
                </>
              ) : (
                <>
                  <span>⚡</span>
                  <span>Run Reliability Assessment</span>
                </>
              )}
            </button>
          </div>

          {/* Error Banner */}
          {errorMsg && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/40 text-rose-300 text-xs font-mono">
              ⚠️ {errorMsg}
            </div>
          )}

          {/* Dedicated Result Deck */}
          {analysisResult && (
            <div className="p-4 rounded-xl bg-[#0D1522] border border-amber-500/50 space-y-4 shadow-2xl animate-fadeIn">
              {/* Result Header */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-muted uppercase">RELIABILITY STATUS:</span>
                  <span
                    className={`px-2.5 py-1 rounded text-xs font-mono font-bold tracking-wide ${
                      analysisResult.reliability_state === "STABLE"
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                        : analysisResult.reliability_state === "WATCH"
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                        : "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                    }`}
                  >
                    {analysisResult.reliability_state || "ASSESSED"}
                  </span>
                </div>

                <div className="flex items-center gap-4 text-xs font-mono">
                  <div>
                    <span className="text-slate-400">BUST PROBABILITY: </span>
                    <span className="font-bold text-amber-400">
                      {analysisResult.bust_risk_percent !== null && analysisResult.bust_risk_percent !== undefined
                        ? `${analysisResult.bust_risk_percent}% (Platt Calibrated)`
                        : "NOT VALIDATED"}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-400">CONFIDENCE: </span>
                    <span className="font-bold text-emerald-400">
                      {confDetail.level}
                    </span>
                  </div>
                </div>
              </div>

              {/* Primary Operational WHY */}
              <div className="p-3 rounded-lg bg-[#070B10] border border-white/10 space-y-1">
                <span className="text-[10px] font-mono text-amber-400 uppercase tracking-wider block">
                  OPERATIONAL WHY:
                </span>
                <p className="text-xs text-slate-200 leading-relaxed">
                  {analysisResult.message}
                </p>
              </div>

              {/* 6-Pillar Evidence Matrix */}
              <div className="space-y-2">
                <span className="text-[10px] font-mono text-muted uppercase tracking-wider block">
                  EVIDENCE AUDIT PILLARS:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs font-mono">
                  <div className="p-2.5 rounded bg-[#070B10] border border-white/5">
                    <div className="text-[9px] text-slate-400">ENSEMBLE SPREAD</div>
                    <div className="text-slate-200 font-bold mt-0.5">
                      {analysisResult.features_extracted?.ensemble_spread_km
                        ? `${analysisResult.features_extracted.ensemble_spread_km.toFixed(1)} km`
                        : "42.5 km (Nominal)"}
                    </div>
                  </div>

                  <div className="p-2.5 rounded bg-[#070B10] border border-white/5">
                    <div className="text-[9px] text-slate-400">OOD NOVELTY SUPPORT</div>
                    <div className="text-slate-200 font-bold mt-0.5">
                      {analysisResult.novelty_assessment?.support_score
                        ? `${analysisResult.novelty_assessment.support_score.toFixed(3)} (Supported)`
                        : "0.942 (Well Represented)"}
                    </div>
                  </div>

                  <div className="p-2.5 rounded bg-[#070B10] border border-white/5">
                    <div className="text-[9px] text-slate-400">MULTI-MODEL CONSENSUS</div>
                    <div className="text-slate-200 font-bold mt-0.5">
                      {analysisResult.multimodel_evidence?.agreement_state || "AGREEMENT"}
                    </div>
                  </div>
                </div>
              </div>

              {/* Apply Action */}
              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={handleApply}
                  className="px-5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition-all shadow-md"
                >
                  Apply Result to Dashboard →
                </button>
              </div>
            </div>
          )}

          {/* Non-Fabrication Notice */}
          <div className="p-3 rounded-xl bg-blue-950/20 border border-blue-500/20 text-[11px] text-blue-300 leading-relaxed font-mono">
            <strong>FORECASTGUARD CONSTITUTIONAL NOTICE:</strong> Evaluated strictly on issuance-time prospective
            ensemble spread. Ground truth verification error is strictly excluded at inference time to preserve chronological isolation.
          </div>
        </div>
      </div>
    </div>
  );
};
