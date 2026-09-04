import React, { useState, useEffect, useCallback } from "react";

interface HealthStatus {
  status: string;
  service: string;
  version: string;
  environment: string;
}

type ConnectionState = "connected" | "connecting" | "disconnected";

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting");
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [lastChecked, setLastChecked] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const checkHealth = useCallback(async () => {
    setConnectionState("connecting");
    setErrorMessage(null);
    const startTime = performance.now();

    try {
      // Determine API URL: Vite proxy handles /api, or fallback to direct origin
      const apiUrl = "/api/v1/health";
      const response = await fetch(apiUrl, {
        headers: { Accept: "application/json" },
      });

      const elapsed = Math.round(performance.now() - startTime);
      setLatencyMs(elapsed);

      if (response.ok) {
        const data: HealthStatus = await response.json();
        setHealth(data);
        setConnectionState("connected");
        setLastChecked(new Date().toLocaleTimeString());
      } else {
        setConnectionState("disconnected");
        setErrorMessage(`HTTP Error: ${response.status} ${response.statusText}`);
        setLastChecked(new Date().toLocaleTimeString());
      }
    } catch (err: unknown) {
      const elapsed = Math.round(performance.now() - startTime);
      setLatencyMs(elapsed);
      setConnectionState("disconnected");
      const message = err instanceof Error ? err.message : "Failed to connect to backend";
      setErrorMessage(message);
      setLastChecked(new Date().toLocaleTimeString());
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const timer = setInterval(checkHealth, 15000);
    return () => clearInterval(timer);
  }, [checkHealth]);

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-logo" aria-label="ForecastGuard Logo">
            <svg viewBox="0 0 24 24">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <div className="brand-info">
            <h1>ForecastGuard</h1>
            <span>Forecast Reliability Intelligence</span>
          </div>
        </div>

        <div className="header-status">
          <div className={`status-chip ${connectionState}`}>
            <span className="pulse-dot" />
            <span>Backend: {connectionState}</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Milestone Foundation Notice */}
        <section className="operational-banner">
          <h2>Milestone Foundation — Operational Health Monitor</h2>
          <p>
            ForecastGuard foundation is active. This operational shell monitors backend API availability
            and service readiness. In accordance with <code>AGENTS.md</code> and <code>ARCHITECTURE.md</code>,
            no machine learning models, bust predictions, or fabricated weather data are loaded.
          </p>
        </section>

        {/* Status and Diagnostics Cards Grid */}
        <div className="cards-grid">
          {/* Health Details Card */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Backend Service Health</span>
              <span className="card-badge">GET /api/v1/health</span>
            </div>

            <div className="metric-row">
              <span className="metric-label">Connection Status</span>
              <span className="metric-value">
                {connectionState === "connected" && (
                  <span style={{ color: "var(--semantic-stable)" }}>ONLINE (200 OK)</span>
                )}
                {connectionState === "connecting" && (
                  <span style={{ color: "var(--semantic-watch)" }}>CHECKING...</span>
                )}
                {connectionState === "disconnected" && (
                  <span style={{ color: "var(--semantic-high-risk)" }}>OFFLINE</span>
                )}
              </span>
            </div>

            <div className="metric-row">
              <span className="metric-label">Service Identifier</span>
              <span className="metric-value code">
                {health?.service || "N/A"}
              </span>
            </div>

            <div className="metric-row">
              <span className="metric-label">API Version</span>
              <span className="metric-value code">
                {health?.version ? `v${health.version}` : "N/A"}
              </span>
            </div>

            <div className="metric-row">
              <span className="metric-label">Environment</span>
              <span className="metric-value code">
                {health?.environment || "N/A"}
              </span>
            </div>

            <div className="metric-row">
              <span className="metric-label">Round-trip Latency</span>
              <span className="metric-value">
                {latencyMs !== null ? `${latencyMs} ms` : "—"}
              </span>
            </div>

            <div className="metric-row">
              <span className="metric-label">Last Checked</span>
              <span className="metric-value">
                {lastChecked || "—"}
              </span>
            </div>

            {errorMessage && (
              <div style={{ marginTop: "1rem", color: "var(--semantic-high-risk)", fontSize: "0.8rem" }}>
                Error: {errorMessage}
              </div>
            )}

            <div className="controls-bar">
              <button
                type="button"
                className="btn btn-primary"
                onClick={checkHealth}
                disabled={connectionState === "connecting"}
              >
                {connectionState === "connecting" ? "Checking..." : "Refresh Health Check"}
              </button>
            </div>
          </div>

          {/* Raw Payload Card */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Live API Response Contract</span>
              <span className="card-badge">application/json</span>
            </div>

            <pre className="code-block">
              {health
                ? JSON.stringify(health, null, 2)
                : connectionState === "connecting"
                ? "{\n  \"status\": \"requesting...\"\n}"
                : "{\n  \"error\": \"Endpoint unreachable\"\n}"}
            </pre>

            <div style={{ marginTop: "1rem", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              Endpoint verifies API runtime without returning premature scientific or simulated forecast state.
            </div>
          </div>

          {/* System Specification Reference Card */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Architectural Principles</span>
              <span className="card-badge">CONSTITUTION</span>
            </div>

            <div className="metric-row">
              <span className="metric-label">Data Integrity</span>
              <span className="metric-value" style={{ color: "var(--semantic-stable)" }}>
                Zero Fabricated Data
              </span>
            </div>

            <div className="metric-row">
              <span className="metric-label">Information Flow</span>
              <span className="metric-value">No Future Leakage</span>
            </div>

            <div className="metric-row">
              <span className="metric-label">Complexity Rule</span>
              <span className="metric-value">Earned by Validation</span>
            </div>

            <div className="metric-row">
              <span className="metric-label">Next Milestone</span>
              <span className="metric-value" style={{ color: "var(--accent-amber)" }}>
                M1 — Real Data Ingestion
              </span>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <div>ForecastGuard — Decision-Support Intelligence for Numerical Weather Prediction</div>
        <div>SIH2026 Problem Statement SIH26079</div>
      </footer>
    </div>
  );
};
