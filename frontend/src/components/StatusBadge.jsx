import React from "react";

const STATUS_CONFIG = {
  PENDING_TRIAGE: { label: "Pending Triage", className: "badge-amber" },
  DRAFT: { label: "Pending Triage", className: "badge-amber" },
  READY_TO_COMMIT: { label: "Ready to Commit", className: "badge-blue" },
  COMMITTED: { label: "Committed", className: "badge-green" },
};

export default function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.PENDING_TRIAGE;
  return <span className={`status-badge ${config.className}`}>{config.label}</span>;
}
