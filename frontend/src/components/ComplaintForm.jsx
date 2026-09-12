import React from "react";
import { useDispatch, useSelector } from "react-redux";
import FormField from "./FormField";
import StatusBadge from "./StatusBadge";
import RiskAssessmentCard from "./RiskAssessmentCard";
import BonusInsightsCard from "./BonusInsightsCard";
import { resetForm, commitToLedger } from "../store/slices/complaintSlice";

export default function ComplaintForm() {
  const dispatch = useDispatch();
  const {
    complaintId,
    complaintNumber,
    status,
    fields,
    confidence,
    missingFields,
    riskAssessment,
    duplicates,
    rootCause,
    capa,
    commitStatus,
  } = useSelector((s) => s.complaint);

  const canCommit = Boolean(complaintId) && status !== "COMMITTED" && commitStatus !== "committing";

  const handleCommit = () => {
    dispatch(commitToLedger({ complaintId, fields, reviewerName: "Demo QA Reviewer" }));
  };

  const handleReset = () => {
    if (window.confirm("Reset the form? Any unsaved AI extraction will be cleared.")) {
      dispatch(resetForm());
    }
  };

  return (
    <div className="complaint-form">
      <header className="form-header">
        <div>
          <h1>Log Customer Complaint</h1>
          <p className="subtitle">API &amp; FDF Quality Assurance Module</p>
        </div>
        <StatusBadge status={status} />
      </header>

      {complaintNumber && (
        <div className="complaint-number-strip">
          Complaint&nbsp;ID: <strong>{complaintNumber}</strong>
        </div>
      )}

      <section className="card">
        <h3 className="card-title">1. Origin &amp; Customer Details</h3>
        <div className="field-grid two-col">
          <FormField field="complaint_source" label="Complaint Source" value={fields.complaint_source} confidence={confidence.complaint_source} />
          <FormField field="customer_name" label="Customer Name" value={fields.customer_name} confidence={confidence.customer_name} />
        </div>
      </section>

      <section className="card">
        <h3 className="card-title">2. Product &amp; Batch Identification</h3>
        <div className="field-grid two-col">
          <FormField field="product_name" label="Product Name" value={fields.product_name} confidence={confidence.product_name} />
          <FormField field="product_strength_grade" label="Product Strength / Grade" value={fields.product_strength_grade} confidence={confidence.product_strength_grade} />
          <FormField field="batch_lot_number" label="Batch / Lot Number" value={fields.batch_lot_number} confidence={confidence.batch_lot_number} />
          <FormField field="affected_quantity" label="Affected Quantity" value={fields.affected_quantity} confidence={confidence.affected_quantity} />
          <FormField field="manufacturing_date" label="Manufacturing Date" value={fields.manufacturing_date} confidence={confidence.manufacturing_date} />
          <FormField field="expiry_date" label="Expiry Date" value={fields.expiry_date} confidence={confidence.expiry_date} />
        </div>
      </section>

      <section className="card">
        <h3 className="card-title">3. Facility &amp; Material Impact</h3>
        <div className="field-grid two-col">
          <FormField field="originating_site_block" label="Originating Site / Block" value={fields.originating_site_block} confidence={confidence.originating_site_block} />
          <FormField field="impacted_npm" label="Impacted Non-Product Materials (NPM)" value={fields.impacted_npm} confidence={confidence.impacted_npm} />
        </div>
      </section>

      <section className="card">
        <h3 className="card-title">4. Defect Analysis</h3>
        <div className="field-grid one-col">
          <FormField field="complaint_category" label="Complaint Category" value={fields.complaint_category} confidence={confidence.complaint_category} />
          <FormField
            field="complaint_description"
            label="Complaint Description / Structured Defect Summary"
            value={fields.complaint_description}
            confidence={confidence.complaint_description}
            multiline
          />
        </div>
      </section>

      <RiskAssessmentCard riskAssessment={riskAssessment} />
      <BonusInsightsCard duplicates={duplicates} rootCause={rootCause} capa={capa} />

      {missingFields?.length > 0 && (
        <div className="missing-fields-banner">
          <strong>Missing information:</strong> {missingFields.join(", ")}. AI does not fabricate these — please
          provide them via the Copilot or fill them in directly.
        </div>
      )}

      <footer className="form-actions">
        <button type="button" className="btn btn-secondary" onClick={handleReset}>
          Reset Form
        </button>
        <button type="button" className="btn btn-primary" onClick={handleCommit} disabled={!canCommit}>
          {commitStatus === "committing"
            ? "Committing..."
            : status === "COMMITTED"
            ? "Committed to QMS Ledger"
            : "Commit to QMS Ledger"}
        </button>
      </footer>
    </div>
  );
}
