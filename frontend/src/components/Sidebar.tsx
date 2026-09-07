import React from "react";

interface SidebarProps {
  activeTab: string;
  onSelectTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onSelectTab }) => {
  return (
    <aside className="system-sidebar">
      {/* Command Center Root */}
      <div className="sidebar-brand-section">
        <div className="sidebar-group-header">COMMAND CENTER</div>
        <button
          className={`sidebar-nav-item active-dashboard ${activeTab === "dashboard" ? "active" : ""}`}
          onClick={() => onSelectTab("dashboard")}
        >
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
          </svg>
          <span className="nav-label">Dashboard</span>
        </button>
      </div>

      <nav className="sidebar-nav-tree">
        {/* MONITOR */}
        <div className="nav-category">
          <div className="category-title">MONITOR</div>
          <button
            className={`sidebar-nav-item ${activeTab === "alerts" ? "active" : ""}`}
            onClick={() => onSelectTab("alerts")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            <span className="nav-label">Active Alerts</span>
            <span className="nav-alert-pill">2</span>
          </button>

          <button
            className={`sidebar-nav-item ${activeTab === "cases" ? "active" : ""}`}
            onClick={() => onSelectTab("cases")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span className="nav-label">Forecast Cases</span>
          </button>

          <button
            className={`sidebar-nav-item ${activeTab === "map" ? "active" : ""}`}
            onClick={() => onSelectTab("map")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
              <line x1="8" y1="2" x2="8" y2="18" />
              <line x1="16" y1="6" x2="16" y2="22" />
            </svg>
            <span className="nav-label">Reliability Map</span>
          </button>
        </div>

        {/* INVESTIGATE */}
        <div className="nav-category">
          <div className="category-title">INVESTIGATE</div>
          <button
            className={`sidebar-nav-item ${activeTab === "explorer" ? "active" : ""}`}
            onClick={() => onSelectTab("explorer")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <span className="nav-label">Forecast Explorer</span>
          </button>

          <button
            className={`sidebar-nav-item ${activeTab === "ensemble" ? "active" : ""}`}
            onClick={() => onSelectTab("ensemble")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            <span className="nav-label">Ensemble Analysis</span>
          </button>

          <button
            className={`sidebar-nav-item ${activeTab === "fields" ? "active" : ""}`}
            onClick={() => onSelectTab("fields")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" />
            </svg>
            <span className="nav-label">Atmospheric Fields</span>
          </button>

          <button
            className={`sidebar-nav-item ${activeTab === "multimodel" ? "active" : ""}`}
            onClick={() => onSelectTab("multimodel")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
            <span className="nav-label">Multi-Model Comparison</span>
          </button>
        </div>

        {/* VERIFY */}
        <div className="nav-category">
          <div className="category-title">VERIFY</div>
          <button
            className={`sidebar-nav-item ${activeTab === "verify" ? "active" : ""}`}
            onClick={() => onSelectTab("verify")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <span className="nav-label">Verification</span>
          </button>

          <button
            className={`sidebar-nav-item ${activeTab === "forecast_vs_reality" ? "active" : ""}`}
            onClick={() => onSelectTab("forecast_vs_reality")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span className="nav-label">Forecast vs Reality</span>
          </button>

          <button
            className={`sidebar-nav-item ${activeTab === "fingerprint" ? "active" : ""}`}
            onClick={() => onSelectTab("fingerprint")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
            </svg>
            <span className="nav-label">Failure Fingerprint</span>
          </button>
        </div>

        {/* MEMORY */}
        <div className="nav-category">
          <div className="category-title">MEMORY</div>
          <button
            className={`sidebar-nav-item ${activeTab === "analogues" ? "active" : ""}`}
            onClick={() => onSelectTab("analogues")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
            </svg>
            <span className="nav-label">Historical Analogues</span>
          </button>

          <button
            className={`sidebar-nav-item ${activeTab === "atlas" ? "active" : ""}`}
            onClick={() => onSelectTab("atlas")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
            <span className="nav-label">Bust Atlas</span>
          </button>
        </div>

        {/* RESEARCH */}
        <div className="nav-category">
          <div className="category-title">RESEARCH</div>
          <button
            className={`sidebar-nav-item ${activeTab === "calibration" ? "active" : ""}`}
            onClick={() => onSelectTab("calibration")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="4" y1="21" x2="4" y2="14" />
              <line x1="4" y1="10" x2="4" y2="3" />
              <line x1="12" y1="21" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12" y2="3" />
              <line x1="20" y1="21" x2="20" y2="16" />
              <line x1="20" y1="12" x2="20" y2="3" />
            </svg>
            <span className="nav-label">Calibration</span>
          </button>

          <button
            className={`sidebar-nav-item ${activeTab === "ablations" ? "active" : ""}`}
            onClick={() => onSelectTab("ablations")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            <span className="nav-label">Ablations</span>
          </button>

          <button
            className={`sidebar-nav-item ${activeTab === "evidence" ? "active" : ""}`}
            onClick={() => onSelectTab("evidence")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
            <span className="nav-label">Evidence & Data</span>
          </button>

          <button
            className={`sidebar-nav-item ${activeTab === "statistics" ? "active" : ""}`}
            onClick={() => onSelectTab("statistics")}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 3v18h18" />
              <path d="m19 9-5 5-4-4-3 3" />
            </svg>
            <span className="nav-label">Statistics</span>
          </button>
        </div>
      </nav>

      {/* SIH 26079 Bottom Footer Emblem */}
      <div className="sidebar-bottom-emblem">
        <div className="sih-emblem-badge">
          <div className="sih-trophy-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="#F5B83D" strokeWidth="1.8">
              <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
              <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
              <path d="M4 22h16" />
              <path d="M10 14.66V17c0 .55-.45 1-1 1H7v2h10v-2h-2c-.55 0-1-.45-1-1v-2.34" />
              <path d="M6 4h12v7a6 6 0 0 1-12 0V4Z" />
            </svg>
          </div>
          <div className="sih-text-group">
            <span className="sih-code">SIH 26079</span>
            <span className="sih-agency">Ministry of Earth Sciences</span>
          </div>
        </div>
        <div className="sih-quote">
          "More Reliable Forecasts for a Safer India"
        </div>
      </div>
    </aside>
  );
};
