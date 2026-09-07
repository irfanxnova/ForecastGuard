import React, { useState, useEffect, useCallback } from "react";
import { TopBar } from "./components/TopBar";
import { Sidebar } from "./components/Sidebar";
import { HeroMap } from "./components/HeroMap";
import { ReliabilityStatus } from "./components/ReliabilityStatus";
import { ReliabilityTrajectory } from "./components/ReliabilityTrajectory";
import { WhyReliabilityLow } from "./components/WhyReliabilityLow";
import { AtmosphericContext } from "./components/AtmosphericContext";
import { HistoricalMatches } from "./components/HistoricalMatches";
import { EnsembleOutlook } from "./components/EnsembleOutlook";
import { ForecastVsObserved } from "./components/ForecastVsObserved";
import { DataEvidenceStatus } from "./components/DataEvidenceStatus";
import { Footer } from "./components/Footer";

// 16 Dedicated Analytical Views
import { ActiveAlertsView } from "./components/views/ActiveAlertsView";
import { ForecastCasesView } from "./components/views/ForecastCasesView";
import { ReliabilityMapView } from "./components/views/ReliabilityMapView";
import { ForecastExplorerView } from "./components/views/ForecastExplorerView";
import { EnsembleAnalysisView } from "./components/views/EnsembleAnalysisView";
import { AtmosphericFieldsView } from "./components/views/AtmosphericFieldsView";
import { MultiModelComparisonView } from "./components/views/MultiModelComparisonView";
import { VerificationView } from "./components/views/VerificationView";
import { ForecastVsRealityView } from "./components/views/ForecastVsRealityView";
import { FailureFingerprintView } from "./components/views/FailureFingerprintView";
import { HistoricalAnaloguesView } from "./components/views/HistoricalAnaloguesView";
import { BustAtlasView } from "./components/views/BustAtlasView";
import { CalibrationView } from "./components/views/CalibrationView";
import { AblationsView } from "./components/views/AblationsView";
import { EvidenceDataView } from "./components/views/EvidenceDataView";
import { StatisticsView } from "./components/views/StatisticsView";

import { DEMO_DASHBOARD_STATE, OPERATIONAL_LIVE_STATE } from "./data/operationalData";
import { buildCycloneDashboardState, STORMS_CATALOG } from "./data/casesData";
import { DashboardState } from "./types/dashboard";

export const App: React.FC = () => {
  // Operational mode: 0 = Historical Replay, 1 = Scenario Demo, 2 = Live Inference
  const [modeIndex, setModeIndex] = useState<number>(0);

  // Active case state
  const [activeStorm, setActiveStorm] = useState<string>("MIDHILI");
  const [activeCycle, setActiveCycle] = useState<string>("MIDHILI_00Z");
  const [isObservationRevealed, setIsObservationRevealed] = useState<boolean>(false);

  // Initial dashboard state is MIDHILI with ground truth withheld
  const [dashboardState, setDashboardState] = useState<DashboardState>(() =>
    buildCycloneDashboardState("MIDHILI", "MIDHILI_00Z", "+24h", false)
  );

  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [backendOnline, setBackendOnline] = useState<boolean>(false);

  // Probe backend health API
  const probeBackend = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/health");
      if (res.ok) {
        setBackendOnline(true);
      }
    } catch {
      setBackendOnline(false);
    }
  }, []);

  useEffect(() => {
    probeBackend();
    const interval = setInterval(probeBackend, 30000);
    return () => clearInterval(interval);
  }, [probeBackend]);

  // Mode cycle toggle (Historical Replay <-> Scenario Demo <-> Live Inference)
  const handleToggleDemoMode = () => {
    const nextIndex = (modeIndex + 1) % 3;
    setModeIndex(nextIndex);
    if (nextIndex === 0) {
      setDashboardState(buildCycloneDashboardState(activeStorm, activeCycle, dashboardState.selectedLead || "+24h", isObservationRevealed));
    } else if (nextIndex === 1) {
      setDashboardState(DEMO_DASHBOARD_STATE);
    } else {
      setDashboardState(OPERATIONAL_LIVE_STATE);
    }
  };

  // Storm selection handler
  const handleSelectStorm = (stormName: string, cycleLabel?: string) => {
    const storm = STORMS_CATALOG.find((s) => s.name.toUpperCase() === stormName.toUpperCase()) || STORMS_CATALOG[0];
    const targetCycle = cycleLabel || storm.defaultCycle;
    setActiveStorm(storm.name);
    setActiveCycle(targetCycle);

    if (modeIndex === 0) {
      const newState = buildCycloneDashboardState(
        storm.name,
        targetCycle,
        dashboardState.selectedLead || "+24h",
        isObservationRevealed
      );
      setDashboardState(newState);
    }
  };

  // Lead time selection handler
  const handleSelectLead = (lead: string) => {
    if (modeIndex === 0) {
      const newState = buildCycloneDashboardState(
        activeStorm,
        activeCycle,
        lead,
        isObservationRevealed
      );
      setDashboardState(newState);
    } else {
      setDashboardState((prev) => ({
        ...prev,
        selectedLead: lead,
        cycle: {
          ...prev.cycle,
          targetLead: lead,
        },
      }));
    }
  };

  // Observation progressive reveal handler
  const handleToggleObservationReveal = () => {
    const nextRevealed = !isObservationRevealed;
    setIsObservationRevealed(nextRevealed);
    if (modeIndex === 0) {
      const newState = buildCycloneDashboardState(
        activeStorm,
        activeCycle,
        dashboardState.selectedLead || "+24h",
        nextRevealed
      );
      setDashboardState(newState);
    } else {
      setDashboardState((prev) => ({
        ...prev,
        isObservationRevealed: nextRevealed,
      }));
    }
  };

  const handleSelectVariable = (variable: string) => {
    setDashboardState((prev) => ({ ...prev, selectedVariable: variable }));
  };

  const handleSelectView = (view: string) => {
    setDashboardState((prev) => ({ ...prev, selectedView: view }));
  };

  // Smooth scroll to explanation panel
  const handleInvestigateClick = () => {
    const el = document.getElementById("why-reliability-low");
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("highlight-panel-pulse");
      setTimeout(() => el.classList.remove("highlight-panel-pulse"), 2000);
    }
  };

  // Render appropriate sidebar sub-view
  const renderActiveView = () => {
    switch (activeTab) {
      // MONITOR
      case "alerts":
        return (
          <ActiveAlertsView
            state={dashboardState}
            onSelectStorm={handleSelectStorm}
            onNavigateTab={setActiveTab}
          />
        );
      case "cases":
        return (
          <ForecastCasesView
            state={dashboardState}
            onSelectStorm={handleSelectStorm}
            onNavigateTab={setActiveTab}
          />
        );
      case "map":
        return (
          <ReliabilityMapView
            state={dashboardState}
            onSelectLead={handleSelectLead}
            onSelectStorm={handleSelectStorm}
            onToggleObservationReveal={handleToggleObservationReveal}
            onNavigateTab={setActiveTab}
          />
        );

      // INVESTIGATE
      case "explorer":
        return (
          <ForecastExplorerView
            state={dashboardState}
            onSelectLead={handleSelectLead}
            onNavigateTab={setActiveTab}
          />
        );
      case "ensemble":
        return (
          <EnsembleAnalysisView
            state={dashboardState}
            onSelectLead={handleSelectLead}
            onNavigateTab={setActiveTab}
          />
        );
      case "fields":
        return (
          <AtmosphericFieldsView
            state={dashboardState}
            onNavigateTab={setActiveTab}
          />
        );
      case "multimodel":
        return (
          <MultiModelComparisonView
            state={dashboardState}
            onNavigateTab={setActiveTab}
          />
        );

      // VERIFY
      case "verify":
        return (
          <VerificationView
            state={dashboardState}
            onNavigateTab={setActiveTab}
          />
        );
      case "forecast_vs_reality":
        return (
          <ForecastVsRealityView
            state={dashboardState}
            onSelectLead={handleSelectLead}
            onSelectStorm={handleSelectStorm}
            onNavigateTab={setActiveTab}
          />
        );
      case "fingerprint":
        return (
          <FailureFingerprintView
            state={dashboardState}
            onNavigateTab={setActiveTab}
            onSelectStorm={handleSelectStorm}
          />
        );

      // MEMORY
      case "analogues":
        return (
          <HistoricalAnaloguesView
            state={dashboardState}
            onNavigateTab={setActiveTab}
            onSelectStorm={handleSelectStorm}
          />
        );
      case "atlas":
        return (
          <BustAtlasView
            state={dashboardState}
            onNavigateTab={setActiveTab}
            onSelectStorm={handleSelectStorm}
            onSelectLead={handleSelectLead}
          />
        );

      // RESEARCH
      case "calibration":
        return (
          <CalibrationView
            state={dashboardState}
            onNavigateTab={setActiveTab}
          />
        );
      case "ablations":
        return (
          <AblationsView
            state={dashboardState}
            onNavigateTab={setActiveTab}
          />
        );
      case "evidence":
        return (
          <EvidenceDataView
            state={dashboardState}
            onNavigateTab={setActiveTab}
          />
        );
      case "statistics":
        return (
          <StatisticsView
            state={dashboardState}
            onNavigateTab={setActiveTab}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="forecastguard-app">
      {/* Top Operational Strip */}
      <TopBar state={dashboardState} onToggleDemoMode={handleToggleDemoMode} backendOnline={backendOnline} />

      {/* Main Body: Sidebar + Command Grid / Analytical Views */}
      <div className="app-body-layout">
        <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} />

        {activeTab === "dashboard" ? (
          <main className="main-command-center">
            {/* Row 1: Hero Map (58%) + Reliability Status (42%) */}
            <div className="grid-row-hero">
              <HeroMap
                state={dashboardState}
                onSelectLead={handleSelectLead}
                onSelectVariable={handleSelectVariable}
                onSelectView={handleSelectView}
              />
              <ReliabilityStatus
                state={dashboardState}
                onInvestigateClick={handleInvestigateClick}
                onToggleObservationReveal={handleToggleObservationReveal}
                onSelectStorm={handleSelectStorm}
                onAssessReliability={handleInvestigateClick}
              />
            </div>

            {/* Row 2: Reliability Trajectory (38%) + Why Low (32%) + Atmospheric Context (30%) */}
            <div className="grid-row-middle">
              <ReliabilityTrajectory
                state={dashboardState}
                onSelectLead={handleSelectLead}
              />
              <WhyReliabilityLow state={dashboardState} />
              <AtmosphericContext state={dashboardState} />
            </div>

            {/* Row 3: Four Equal Bottom Analytical Cards */}
            <div className="grid-row-bottom">
              <HistoricalMatches state={dashboardState} />
              <EnsembleOutlook state={dashboardState} />
              <ForecastVsObserved state={dashboardState} />
              <DataEvidenceStatus state={dashboardState} />
            </div>
          </main>
        ) : (
          <main className="main-command-center sub-view-container">
            {renderActiveView()}
          </main>
        )}
      </div>

      {/* Operational Footer */}
      <Footer />
    </div>
  );
};
