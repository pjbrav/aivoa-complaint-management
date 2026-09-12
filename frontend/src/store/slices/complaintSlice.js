import { createSlice, createAsyncThunk, nanoid } from "@reduxjs/toolkit";
import { EMPTY_COMPLAINT_FIELDS } from "../../types/complaint";
import * as api from "../../services/api";

/**
 * Design note: this slice is the ONLY place structured complaint state
 * lives. The Copilot never "writes into the form" by manipulating the
 * DOM or parsing chat text on the frontend — every AI response arrives
 * as structured JSON (ExtractionResponse / ChatResponse) from the
 * backend, and reducers merge it into `fields`. This is what the
 * assignment means by "don't rely on scraping AI-generated text to
 * populate form fields."
 */

const initialState = {
  complaintId: null,
  complaintNumber: null,
  status: "PENDING_TRIAGE", // PENDING_TRIAGE | DRAFT | READY_TO_COMMIT | COMMITTED
  fields: { ...EMPTY_COMPLAINT_FIELDS },
  confidence: {},
  missingFields: [],
  riskAssessment: null, // { severity, suggested_next_action, initial_risk_assessment }
  completeness: null, // { complete, missing_fields }
  duplicates: [],
  rootCause: null,
  capa: null,
  messages: [
    {
      id: "welcome",
      role: "assistant",
      text:
        "I can process a new complaint. Paste raw customer email/text, upload a PDF complaint report, " +
        "and I'll extract the details, classify the complaint, and run an initial risk assessment.",
      timestamp: new Date().toISOString(),
    },
  ],
  uploadedFile: null, // { name }
  processingState: "idle", // idle | processing | error
  processingLabel: null,
  commitStatus: "idle", // idle | committing | committed | error
  validationErrors: {},
  error: null,
};

function statusFromExtraction(payload) {
  return payload.status || "DRAFT";
}

function mergeFields(current, updates) {
  const next = { ...current };
  Object.entries(updates || {}).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    if (typeof value === "string" && value.trim() === "") return;
    next[key] = value;
  });
  return next;
}

// --- Thunks -----------------------------------------------------------

export const submitComplaintText = createAsyncThunk(
  "complaint/submitText",
  async (text, { rejectWithValue }) => {
    try {
      return await api.processText(text);
    } catch (err) {
      return rejectWithValue(api.extractErrorMessage(err));
    }
  }
);

export const submitComplaintPdf = createAsyncThunk(
  "complaint/submitPdf",
  async (file, { rejectWithValue }) => {
    try {
      return await api.processPdf(file);
    } catch (err) {
      return rejectWithValue(api.extractErrorMessage(err));
    }
  }
);

export const sendCopilotMessage = createAsyncThunk(
  "complaint/sendMessage",
  async ({ complaintId, message }, { rejectWithValue }) => {
    try {
      return await api.sendChatMessage(complaintId, message);
    } catch (err) {
      return rejectWithValue(api.extractErrorMessage(err));
    }
  }
);

export const commitToLedger = createAsyncThunk(
  "complaint/commit",
  async ({ complaintId, fields, reviewerName }, { rejectWithValue }) => {
    try {
      return await api.commitComplaint(complaintId, fields, reviewerName);
    } catch (err) {
      return rejectWithValue(api.extractErrorMessage(err));
    }
  }
);

// --- Slice --------------------------------------------------------------

const complaintSlice = createSlice({
  name: "complaint",
  initialState,
  reducers: {
    updateFieldLocally(state, action) {
      const { field, value } = action.payload;
      state.fields[field] = value;
      // A manual edit resolves that field from "missing" immediately in
      // the UI, even before the next AI round-trip recomputes completeness.
      state.missingFields = state.missingFields.filter(
        (label) => label.toLowerCase() !== field.replace(/_/g, " ").toLowerCase()
      );
    },
    addUserMessage(state, action) {
      state.messages.push({
        id: nanoid(),
        role: "user",
        text: action.payload,
        timestamp: new Date().toISOString(),
      });
    },
    setUploadedFile(state, action) {
      state.uploadedFile = action.payload;
    },
    resetForm() {
      return {
        ...initialState,
        messages: [{ ...initialState.messages[0], id: nanoid() }],
      };
    },
    dismissError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // --- process-text ---
      .addCase(submitComplaintText.pending, (state) => {
        state.processingState = "processing";
        state.processingLabel = "Analyzing complaint text and extracting key details...";
        state.error = null;
      })
      .addCase(submitComplaintText.fulfilled, (state, action) => {
        applyExtraction(state, action.payload);
      })
      .addCase(submitComplaintText.rejected, (state, action) => {
        state.processingState = "error";
        state.processingLabel = null;
        state.error = action.payload || "Failed to process complaint text.";
        state.messages.push({
          id: nanoid(),
          role: "assistant",
          text: `I ran into a problem processing that: ${state.error}`,
          timestamp: new Date().toISOString(),
        });
      })

      // --- process-pdf ---
      .addCase(submitComplaintPdf.pending, (state) => {
        state.processingState = "processing";
        state.processingLabel = "Extracting tabular data via OCR...";
        state.error = null;
      })
      .addCase(submitComplaintPdf.fulfilled, (state, action) => {
        applyExtraction(state, action.payload);
      })
      .addCase(submitComplaintPdf.rejected, (state, action) => {
        state.processingState = "error";
        state.processingLabel = null;
        state.error = action.payload || "Failed to process the PDF.";
        state.messages.push({
          id: nanoid(),
          role: "assistant",
          text: `I couldn't process that PDF: ${state.error}`,
          timestamp: new Date().toISOString(),
        });
      })

      // --- chat / corrections ---
      .addCase(sendCopilotMessage.pending, (state) => {
        state.processingState = "processing";
        state.processingLabel = "Updating complaint details...";
        state.error = null;
      })
      .addCase(sendCopilotMessage.fulfilled, (state, action) => {
        applyExtraction(state, action.payload);
      })
      .addCase(sendCopilotMessage.rejected, (state, action) => {
        state.processingState = "error";
        state.processingLabel = null;
        state.error = action.payload || "Failed to process your message.";
        state.messages.push({
          id: nanoid(),
          role: "assistant",
          text: `I couldn't apply that update: ${state.error}`,
          timestamp: new Date().toISOString(),
        });
      })

      // --- commit ---
      .addCase(commitToLedger.pending, (state) => {
        state.commitStatus = "committing";
        state.error = null;
      })
      .addCase(commitToLedger.fulfilled, (state, action) => {
        state.commitStatus = "committed";
        state.status = "COMMITTED";
        state.complaintNumber = action.payload.complaint_number;
        state.messages.push({
          id: nanoid(),
          role: "assistant",
          text: `Complaint ${action.payload.complaint_number} committed successfully.`,
          timestamp: new Date().toISOString(),
        });
      })
      .addCase(commitToLedger.rejected, (state, action) => {
        state.commitStatus = "error";
        state.error = action.payload || "Failed to commit complaint.";
      });
  },
});

function applyExtraction(state, payload) {
  state.processingState = "idle";
  state.processingLabel = null;
  state.complaintId = payload.complaint_id;
  state.complaintNumber = payload.complaint_number;
  state.fields = mergeFields(state.fields, payload.fields);
  state.confidence = payload.confidence || {};
  state.missingFields = payload.missing_fields || [];
  state.riskAssessment = payload.risk_assessment || null;
  state.completeness = payload.completeness || null;
  state.duplicates = payload.duplicates || [];
  state.rootCause = payload.root_cause || null;
  state.capa = payload.capa || null;
  state.status = statusFromExtraction(payload);
  state.messages.push({
    id: nanoid(),
    role: "assistant",
    text: payload.assistant_message,
    timestamp: new Date().toISOString(),
  });
}

export const { updateFieldLocally, addUserMessage, setUploadedFile, resetForm, dismissError } =
  complaintSlice.actions;

export default complaintSlice.reducer;
