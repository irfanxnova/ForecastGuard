import React from "react";

export const Footer: React.FC = () => {
  return (
    <footer className="system-footer-strip">
      <div className="footer-left">
        <span className="footer-item">ForecastGuard v0.1</span>
        <span className="footer-sep">•</span>
        <span className="footer-item">NCMRWF Hackathon 2025</span>
        <span className="footer-sep">•</span>
        <span className="footer-item highlight-sih">SIH 26079</span>
      </div>

      <div className="footer-center">
        <span>Scientific Rigor</span>
        <span className="footer-pipe">|</span>
        <span>Operational Relevance</span>
        <span className="footer-pipe">|</span>
        <span>A More Resilient Tomorrow</span>
      </div>

      <div className="footer-right">
        <span className="footer-tagline">"From Forecasts to Foresight"</span>
      </div>
    </footer>
  );
};
