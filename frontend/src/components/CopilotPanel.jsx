import React, { useRef, useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  submitComplaintText,
  submitComplaintPdf,
  sendCopilotMessage,
  addUserMessage,
  setUploadedFile,
} from "../store/slices/complaintSlice";

export default function CopilotPanel() {
  const dispatch = useDispatch();
  const { complaintId, messages, processingState, processingLabel, uploadedFile, error } = useSelector(
    (s) => s.complaint
  );
  const [inputText, setInputText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, processingState]);

  const isProcessing = processingState === "processing";

  const handleFile = (file) => {
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      window.alert("Only PDF files are supported in this MVP. Please paste the complaint text instead.");
      return;
    }
    dispatch(setUploadedFile({ name: file.name }));
    dispatch(addUserMessage(`📎 Uploaded: ${file.name}`));
    dispatch(submitComplaintPdf(file));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  const handleBrowse = (e) => {
    handleFile(e.target.files?.[0]);
    e.target.value = "";
  };

  const handleSend = () => {
    const text = inputText.trim();
    if (!text || isProcessing) return;

    dispatch(addUserMessage(text));
    setInputText("");

    if (complaintId) {
      // A complaint already exists for this session: treat this message
      // as a correction/follow-up rather than a brand-new complaint.
      dispatch(sendCopilotMessage({ complaintId, message: text }));
    } else {
      dispatch(submitComplaintText(text));
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="copilot-panel">
      <header className="copilot-header">
        <div className="copilot-title-row">
          <span className="copilot-icon">✦</span>
          <h2>AIVOA Copilot</h2>
          <span className="beta-badge">BETA</span>
        </div>
        <p className="copilot-subtitle">Drop complaint files or paste text below.</p>
      </header>

      <div
        className={`dropzone${isDragging ? " dropzone-active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="dropzone-icon">⬆</div>
        <div>
          Drag &amp; drop complaint document here
          <br />
          or <span className="link-text">click to browse</span>
        </div>
        <input ref={fileInputRef} type="file" accept="application/pdf,.pdf" hidden onChange={handleBrowse} />
      </div>
      <p className="dropzone-hint">Supported: PDF &middot; Max 10MB</p>

      {uploadedFile && (
        <div className="attachment-chip">
          📄 {uploadedFile.name}
        </div>
      )}

      {isProcessing && (
        <div className="processing-bar">
          <div className="processing-bar-track">
            <div className="processing-bar-fill" />
          </div>
          <span>{processingLabel || "Processing..."}</span>
        </div>
      )}

      <div className="chat-messages">
        {messages.map((m) => (
          <div key={m.id} className={`chat-message chat-message-${m.role}`}>
            <div className="chat-bubble">{m.text}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {error && <div className="chat-error-banner">{error}</div>}

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          placeholder="Paste complaint text, or ask me to correct a field..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          disabled={isProcessing}
        />
        <button className="send-btn" onClick={handleSend} disabled={isProcessing || !inputText.trim()}>
          ➤
        </button>
      </div>
      <p className="disclaimer-text">AI responses may contain errors. Please verify information before committing.</p>
    </div>
  );
}
