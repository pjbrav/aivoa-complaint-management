import React from "react";

const SEVERITY_CLASS = {
  Minor: "severity-minor",
  Major: "severity-major",
  Critical: "severity-critical",
  "Not Assessed": "severity-none",
};

export default function RiskAssessmentCard({ riskAssessment }) {
  const severity = riskAssessment?.severity || "Not Assessed";
  const nextAction = riskAssessment?.suggested_next_action || "Awaiting AI extraction...";
  const assessment = riskAssessment?.initial_risk_assessment || "Awaiting AI extraction...";

  return (
    <section className="card risk-card">
      <h3 className="card-title">AI Copilot Risk Assessment</h3>
      <p className="risk-disclaimer">
        AI-generated decision support. Requires human QA review before action.
      </p>
      <div className="risk-grid">
        <div>
          <span className="field-label">Severity (Suggested)</span>
          <div className={`severity-pill ${SEVERITY_CLASS[severity] || "severity-none"}`}>{severity}</div>
        </div>
        <div>
          <span className="field-label">Suggested Next Action</span>
          <div className="risk-text">{nextAction}</div>
        </div>
      </div>
      <div className="risk-assessment-block">
        <span className="field-label">Initial Risk Assessment</span>
        <p className="risk-text">{assessment}</p>
      </div>
    </section>
  );
}
