import React, { useState, useEffect } from "react";

interface ForecastUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyAnalyzedForecast: (analysis: any, payload: any) => void;
}

export const ForecastUploadModal: React.FC<ForecastUploadModalProps> = ({
  isOpen,
  onClose,
  onApplyAnalyzedForecast,
}) => {
  const [samples, setSamples] = useState<any[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState<string>("");
  const [forecastPayload, setForecastPayload] = useState<any | null>(null);
  const [validationResult, setValidationResult] = useState<any | null>(null);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Fetch sample forecasts catalog on open
  useEffect(() => {
    if (isOpen) {
      fetch("/api/v1/inference/sample-forecasts")
        .then((res) => res.json())
        .then((data) => {
          if (Array.isArray(data) && data.length > 0) {
            setSamples(data);
            handleSelectSample(data[0]);
          }
        })
        .catch(() => {
          // Fallback if offline
        });
    }
  }, [isOpen]);

  const handleSelectSample = (sample: any) => {
    setSelectedSampleId(sample.sample_id);
    setForecastPayload(sample.payload);
    setAnalysisResult(null);
    setAnalysisError(null);
    triggerValidation(sample.payload);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        const parsed = JSON.parse(text);
        setSelectedSampleId("custom_upload");
        setForecastPayload(parsed);
        setAnalysisResult(null);
        setAnalysisError(null);
        triggerValidation(parsed);
      } catch (err: any) {
        setAnalysisError(`Failed to parse forecast JSON file: ${err.message}`);
        setValidationResult(null);
      }
    };
    reader.readAsText(file);
  };

  const triggerValidation = async (payload: any) => {
    setIsValidating(true);
    setAnalysisError(null);
    try {
      const res = await fetch("/api/v1/inference/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      setValidationResult(data);
    } catch (err: any) {
      setAnalysisError(`Validation failed to connect: ${err.message}`);
    } finally {
      setIsValidating(false);
    }
  };

  const handleRunAnalysis = async () => {
    if (!forecastPayload) return;
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const res = await fetch("/api/v1/inference/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(forecastPayload),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail?.message || errData.detail || "Analysis failed");
      }
      const data = await res.json();
      setAnalysisResult(data);
    } catch (err: any) {
      setAnalysisError(err.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApplyToMap = () => {
    if (analysisResult && forecastPayload) {
      onApplyAnalyzedForecast(analysisResult, forecastPayload);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(5, 8, 12, 0.85)",
        backdropFilter: "blur(6px)",
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
    >
      <div
        className="panel"
        style={{
          width: "100%",
          maxWidth: "880px",
          maxHeight: "90vh",
          overflowY: "auto",
          background: "#0C121B",
          border: "1px solid rgba(245, 184, 61, 0.35)",
          boxShadow: "0 20px 40px rgba(0, 0, 0, 0.7)",
          borderRadius: "8px",
          padding: "24px",
          color: "#E2E8F0",
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "0.08em", color: "#F5B83D" }}>
                CORE OPERATIONAL INPUT FLOW
              </span>
              <span
                style={{
                  fontSize: "10px",
                  padding: "2px 6px",
                  borderRadius: "3px",
                  background: "rgba(69, 183, 209, 0.15)",
                  color: "#45B7D1",
                  border: "1px solid rgba(69, 183, 209, 0.3)",
                  fontWeight: 600,
                }}
              >
                NCMRWF NEPS PIPELINE
              </span>
            </div>
            <h2 style={{ fontSize: "18px", fontWeight: 700, margin: "6px 0 2px 0", color: "#FFFFFF" }}>
              Upload & Analyze Forecast
            </h2>
            <p style={{ fontSize: "11.5px", color: "#94A3B8", margin: 0 }}>
              Input real numerical weather prediction data into ForecastGuard to evaluate prospective bust vulnerability.
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#94A3B8",
              fontSize: "20px",
              cursor: "pointer",
              padding: "4px",
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>

        {/* STEP 1: Select Forecast */}
        <div style={{ marginBottom: "20px" }}>
          <div style={{ fontSize: "11.5px", fontWeight: 700, color: "#CBD5E1", marginBottom: "8px" }}>
            STEP 1: SELECT FORECAST (UPLOAD FILE OR PICK REAL ARCHIVE FIXTURE)
          </div>

          {/* Quick Select Buttons */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "8px", marginBottom: "12px" }}>
            {samples.map((s) => (
              <button
                key={s.sample_id}
                onClick={() => handleSelectSample(s)}
                style={{
                  textAlign: "left",
                  padding: "10px 12px",
                  borderRadius: "4px",
                  background: selectedSampleId === s.sample_id ? "rgba(245, 184, 61, 0.15)" : "#101824",
                  border: selectedSampleId === s.sample_id ? "1px solid #F5B83D" : "1px solid rgba(255, 255, 255, 0.08)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  <span style={{ fontSize: "11px", fontWeight: 700, color: selectedSampleId === s.sample_id ? "#FFD36A" : "#FFFFFF" }}>
                    {s.storm_name}
                  </span>
                  <span
                    style={{
                      fontSize: "9px",
                      padding: "1px 5px",
                      borderRadius: "2px",
                      background: s.verification_mode === "VERIFIED" ? "rgba(85, 217, 138, 0.15)" : "rgba(245, 158, 11, 0.15)",
                      color: s.verification_mode === "VERIFIED" ? "#55D98A" : "#F59E0B",
                      fontWeight: 600,
                    }}
                  >
                    {s.verification_mode === "VERIFIED" ? "VERIFIED" : "PENDING"}
                  </span>
                </div>
                <div style={{ fontSize: "10px", color: "#94A3B8", lineHeight: 1.3 }}>
                  {s.description}
                </div>
              </button>
            ))}
          </div>

          {/* Custom File Upload Option */}
          <div
            style={{
              border: "1px dashed rgba(255, 255, 255, 0.15)",
              borderRadius: "4px",
              padding: "10px 14px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: "#080D14",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#45B7D1" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <span style={{ fontSize: "11px", color: "#CBD5E1" }}>
                Or upload custom forecast JSON payload:
              </span>
            </div>
            <input
              type="file"
              accept=".json"
              onChange={handleFileUpload}
              style={{ fontSize: "11px", color: "#94A3B8" }}
            />
          </div>
        </div>

        {/* STEP 2: Input Contract Validation */}
        {validationResult && (
          <div
            style={{
              background: validationResult.is_valid ? "rgba(85, 217, 138, 0.05)" : "rgba(239, 68, 68, 0.08)",
              border: validationResult.is_valid ? "1px solid rgba(85, 217, 138, 0.3)" : "1px solid rgba(239, 68, 68, 0.4)",
              borderRadius: "6px",
              padding: "14px 16px",
              marginBottom: "20px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, color: validationResult.is_valid ? "#55D98A" : "#EF4444" }}>
                STEP 2: INPUT VALIDATION REPORT — {validationResult.validation_status}
              </span>
              <span
                style={{
                  fontSize: "10px",
                  padding: "2px 8px",
                  borderRadius: "3px",
                  background: validationResult.verification_mode === "HISTORICAL_VERIFIED" ? "rgba(85, 217, 138, 0.15)" : "rgba(245, 158, 11, 0.15)",
                  color: validationResult.verification_mode === "HISTORICAL_VERIFIED" ? "#55D98A" : "#F59E0B",
                  fontWeight: 600,
                }}
              >
                {validationResult.verification_mode === "HISTORICAL_VERIFIED" ? "OBSERVATION PRESENT (VERIFIED MODE)" : "OBSERVATION WITHHELD (PENDING VERIFICATION)"}
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "8px", fontSize: "11px" }}>
              <div>
                <span style={{ color: "#94A3B8" }}>Model Source: </span>
                <strong style={{ color: "#FFFFFF" }}>{validationResult.forecast_source}</strong>
              </div>
              <div>
                <span style={{ color: "#94A3B8" }}>Target Storm: </span>
                <strong style={{ color: "#FFFFFF" }}>{validationResult.cyclone_name}</strong>
              </div>
              <div>
                <span style={{ color: "#94A3B8" }}>Cycle / Step: </span>
                <strong style={{ color: "#FFFFFF" }}>+{validationResult.lead_hours}h ({validationResult.forecast_cycle?.slice(0, 10)})</strong>
              </div>
              <div>
                <span style={{ color: "#94A3B8" }}>Ensemble Members: </span>
                <strong style={{ color: validationResult.ensemble_members_count >= 11 ? "#55D98A" : "#F5B83D" }}>
                  {validationResult.ensemble_members_count}/11 members
                </strong>
              </div>
            </div>

            {validationResult.errors?.length > 0 && (
              <div style={{ marginTop: "10px", color: "#EF4444", fontSize: "10.5px" }}>
                <strong>Blocking Errors:</strong>
                <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                  {validationResult.errors.map((e: string, i: number) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* STEP 3: Action Button */}
        <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
          <button
            disabled={!validationResult?.is_valid || isAnalyzing}
            onClick={handleRunAnalysis}
            style={{
              flex: 1,
              padding: "12px 16px",
              borderRadius: "4px",
              background: validationResult?.is_valid ? "#F5B83D" : "#334155",
              color: validationResult?.is_valid ? "#0B111A" : "#94A3B8",
              fontSize: "13px",
              fontWeight: 700,
              cursor: validationResult?.is_valid && !isAnalyzing ? "pointer" : "not-allowed",
              border: "none",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              transition: "all 0.15s ease",
            }}
          >
            {isAnalyzing ? (
              <>
                <span className="pulse-circle" style={{ width: "8px", height: "8px", background: "#0B111A" }} />
                EXECUTING SCIENTIFIC ANALYSIS...
              </>
            ) : (
              <>
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                STEP 3: ANALYZE FORECAST RELIABILITY
              </>
            )}
          </button>
        </div>

        {analysisError && (
          <div style={{ padding: "10px 14px", background: "rgba(239, 68, 68, 0.12)", color: "#FCA5A5", borderRadius: "4px", fontSize: "11px", marginBottom: "16px" }}>
            {analysisError}
          </div>
        )}

        {/* STEP 4: Operational Analysis Result Screen */}
        {analysisResult && (
          <div
            style={{
              border: "1px solid rgba(245, 184, 61, 0.35)",
              borderRadius: "6px",
              background: "rgba(15, 23, 42, 0.7)",
              padding: "18px 20px",
            }}
          >
            {/* Top Status & Verification Pill */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "8px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span
                  style={{
                    padding: "4px 10px",
                    borderRadius: "4px",
                    fontSize: "12px",
                    fontWeight: 800,
                    letterSpacing: "0.04em",
                    background:
                      analysisResult.reliability_state === "HAZARDOUS_BUST"
                        ? "rgba(239, 68, 68, 0.2)"
                        : analysisResult.reliability_state === "VULNERABLE"
                        ? "rgba(245, 184, 61, 0.2)"
                        : "rgba(85, 217, 138, 0.15)",
                    color:
                      analysisResult.reliability_state === "HAZARDOUS_BUST"
                        ? "#EF4444"
                        : analysisResult.reliability_state === "VULNERABLE"
                        ? "#F5B83D"
                        : "#55D98A",
                    border:
                      analysisResult.reliability_state === "HAZARDOUS_BUST"
                        ? "1px solid rgba(239, 68, 68, 0.4)"
                        : analysisResult.reliability_state === "VULNERABLE"
                        ? "1px solid rgba(245, 184, 61, 0.4)"
                        : "1px solid rgba(85, 217, 138, 0.3)",
                  }}
                >
                  RELIABILITY: {analysisResult.reliability_state} ({analysisResult.bust_risk_percent}% Bust Probability)
                </span>
              </div>

              {/* Verification Status Banner (Strict Guardrail) */}
              <span
                style={{
                  padding: "4px 10px",
                  borderRadius: "4px",
                  fontSize: "11px",
                  fontWeight: 700,
                  background:
                    analysisResult.verification_status === "VERIFIED"
                      ? "rgba(85, 217, 138, 0.15)"
                      : "rgba(148, 163, 184, 0.15)",
                  color:
                    analysisResult.verification_status === "VERIFIED" ? "#55D98A" : "#94A3B8",
                  border:
                    analysisResult.verification_status === "VERIFIED"
                      ? "1px solid rgba(85, 217, 138, 0.3)"
                      : "1px solid rgba(148, 163, 184, 0.3)",
                }}
              >
                {analysisResult.verification_status === "VERIFIED"
                  ? `VERIFIED: ${analysisResult.verification_detail?.outcome || "WITHIN_TOLERANCE"} (Track Error: ${analysisResult.verification_detail?.verified_track_error_km} km vs ${analysisResult.verification_detail?.tolerance_threshold_km} km)`
                  : "STATUS: PENDING VERIFICATION (Observation Withheld / Future Forecast)"}
              </span>
            </div>

            {/* 4 Core Dimensions: WHERE, WHEN, WHY, DATA QUALITY */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px", marginBottom: "16px" }}>
              {/* WHERE */}
              <div style={{ background: "#0D141E", padding: "12px", borderRadius: "4px", border: "1px solid rgba(255, 255, 255, 0.06)" }}>
                <div style={{ fontSize: "10.5px", fontWeight: 700, color: "#45B7D1", marginBottom: "4px" }}>
                  WHERE (AFFECTED REGION)
                </div>
                <div style={{ fontSize: "12px", fontWeight: 600, color: "#FFFFFF" }}>
                  {analysisResult.where.affected_region_label}
                </div>
                <div style={{ fontSize: "10px", color: "#94A3B8", marginTop: "4px" }}>
                  Centroid: {analysisResult.where.centroid_lat}&deg;N, {analysisResult.where.centroid_lon}&deg;E
                </div>
                <div style={{ fontSize: "10px", color: "#94A3B8" }}>
                  Tolerance Radius &tau;(lead): <strong>{analysisResult.where.tolerance_radius_km} km</strong>
                </div>
              </div>

              {/* WHEN */}
              <div style={{ background: "#0D141E", padding: "12px", borderRadius: "4px", border: "1px solid rgba(255, 255, 255, 0.06)" }}>
                <div style={{ fontSize: "10.5px", fontWeight: 700, color: "#F59E0B", marginBottom: "4px" }}>
                  WHEN (LEAD & FAILURE WINDOW)
                </div>
                <div style={{ fontSize: "12px", fontWeight: 600, color: "#FFFFFF" }}>
                  Step: +{analysisResult.when.lead_hours}h Forecast
                </div>
                <div style={{ fontSize: "10px", color: "#94A3B8", marginTop: "4px" }}>
                  Valid: {analysisResult.when.valid_time?.slice(11, 16)} UTC {analysisResult.when.valid_time?.slice(0, 10)}
                </div>
                <div style={{ fontSize: "10px", color: "#FFD36A" }}>
                  Window: {analysisResult.when.expected_failure_window}
                </div>
              </div>

              {/* WHY */}
              <div style={{ background: "#0D141E", padding: "12px", borderRadius: "4px", border: "1px solid rgba(255, 255, 255, 0.06)" }}>
                <div style={{ fontSize: "10.5px", fontWeight: 700, color: "#55D98A", marginBottom: "4px" }}>
                  WHY (PROSPECTIVE EVIDENCE)
                </div>
                <div style={{ fontSize: "10px", color: "#CBD5E1" }}>
                  Ensemble Spread: <strong>{analysisResult.why.ensemble_spread_km} km</strong>
                </div>
                <div style={{ fontSize: "10px", color: "#CBD5E1" }}>
                  Divergence: <strong>{analysisResult.why.ensemble_divergence_km} km</strong>
                </div>
                <div style={{ fontSize: "10px", color: "#CBD5E1" }}>
                  OOD State: <strong>{analysisResult.why.ood_representation_state}</strong> ({analysisResult.why.ood_support_score}/100)
                </div>
              </div>

              {/* PROVENANCE */}
              <div style={{ background: "#0D141E", padding: "12px", borderRadius: "4px", border: "1px solid rgba(255, 255, 255, 0.06)" }}>
                <div style={{ fontSize: "10.5px", fontWeight: 700, color: "#A8B2BD", marginBottom: "4px" }}>
                  DATA PROVENANCE
                </div>
                <div style={{ fontSize: "10px", color: "#CBD5E1" }}>
                  System: {analysisResult.provenance.source_system}
                </div>
                <div style={{ fontSize: "10px", color: "#CBD5E1" }}>
                  Model: {analysisResult.provenance.model_identifier}
                </div>
                <div style={{ fontSize: "10px", color: "#55D98A" }}>
                  Telemetry: Complete 11-member coverage
                </div>
              </div>
            </div>

            {/* Historical Analogue Match Callout */}
            {analysisResult.why.closest_historical_analogue && (
              <div
                style={{
                  background: "rgba(10, 16, 24, 0.6)",
                  borderLeft: "3px solid #45B7D1",
                  padding: "8px 12px",
                  borderRadius: "0 4px 4px 0",
                  fontSize: "11px",
                  color: "#CBD5E1",
                  marginBottom: "16px",
                }}
              >
                <strong style={{ color: "#45B7D1" }}>Historical Memory Analogue: </strong>
                {analysisResult.why.closest_historical_analogue} — {analysisResult.why.analogue_similarity_desc}
              </div>
            )}

            {/* Bottom Action: Load to Map */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button
                onClick={handleApplyToMap}
                style={{
                  padding: "10px 18px",
                  borderRadius: "4px",
                  background: "#55D98A",
                  color: "#051A0E",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: "pointer",
                  border: "none",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
                </svg>
                LOAD INTO OPERATIONAL MAP & COMMAND CENTER
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
