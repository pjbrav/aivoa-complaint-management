import React from "react";

export default function BonusInsightsCard({ duplicates, rootCause, capa }) {
  // Note: completeness/missing-fields are surfaced separately via the
  // missing-fields banner in ComplaintForm.jsx, not duplicated here —
  // this card is only for duplicate/root-cause/CAPA findings, so it
  // should stay hidden rather than render an empty shell when none of
  // those apply.
  const hasAnything =
    (duplicates && duplicates.length) ||
    (rootCause && rootCause.suggested_investigation_areas?.length) ||
    (capa && (capa.corrective_actions?.length || capa.preventive_actions?.length));

  if (!hasAnything) return null;

  return (
    <section className="card bonus-card">
      <h3 className="card-title">Additional AI Insights</h3>

      {duplicates && duplicates.length > 0 && (
        <div className="bonus-block">
          <span className="field-label">Potential Duplicate Complaints</span>
          <ul className="bonus-list">
            {duplicates.map((d) => (
              <li key={d.complaint_id}>
                <strong>{d.complaint_number}</strong> — {Math.round(d.similarity * 100)}% similarity
                {d.matched_on?.length ? ` (matched: ${d.matched_on.join(", ")})` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}

      {rootCause && rootCause.suggested_investigation_areas?.length > 0 && (
        <div className="bonus-block">
          <span className="field-label">AI-Suggested Investigation Areas</span>
          <ul className="bonus-list">
            {rootCause.suggested_investigation_areas.map((area) => (
              <li key={area}>{area}</li>
            ))}
          </ul>
          <p className="bonus-disclaimer">{rootCause.disclaimer}</p>
        </div>
      )}

      {capa && (capa.corrective_actions?.length > 0 || capa.preventive_actions?.length > 0) && (
        <div className="bonus-block">
          <span className="field-label">CAPA Recommendation (Draft)</span>
          {capa.corrective_actions?.length > 0 && (
            <>
              <p className="bonus-subheading">Corrective</p>
              <ul className="bonus-list">
                {capa.corrective_actions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </>
          )}
          {capa.preventive_actions?.length > 0 && (
            <>
              <p className="bonus-subheading">Preventive</p>
              <ul className="bonus-list">
                {capa.preventive_actions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </>
          )}
          <p className="bonus-disclaimer">{capa.disclaimer}</p>
        </div>
      )}
    </section>
  );
}
