import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

/**
 * Every function here returns response.data directly (the parsed
 * ExtractionResponse / ChatResponse / CommitResponse JSON) and lets
 * axios errors propagate — the Redux thunks in complaintSlice.js are
 * responsible for catching them and turning them into user-facing
 * error state, so this file stays a thin, dumb transport layer.
 */

export async function processText(text) {
  const { data } = await client.post("/complaints/process-text", { text });
  return data;
}

export async function processPdf(file) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await client.post("/complaints/process-pdf", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function sendChatMessage(complaintId, message) {
  const { data } = await client.post("/complaints/chat", {
    complaint_id: complaintId,
    message,
  });
  return data;
}

export async function commitComplaint(complaintId, fields, reviewerName) {
  const { data } = await client.post("/complaints/commit", {
    complaint_id: complaintId,
    fields,
    reviewer_name: reviewerName,
  });
  return data;
}

export async function getComplaint(complaintId) {
  const { data } = await client.get(`/complaints/${complaintId}`);
  return data;
}

export async function getAuditLog(complaintId) {
  const { data } = await client.get(`/complaints/${complaintId}/audit-log`);
  return data;
}

export async function listComplaints() {
  const { data } = await client.get("/complaints");
  return data;
}

/** Extracts a clean, user-facing message from an axios error, since the
 * backend always returns { detail: "..." } on failure. */
export function extractErrorMessage(error) {
  return (
    error?.response?.data?.detail ||
    error?.message ||
    "Something went wrong talking to the AIVOA backend."
  );
}
