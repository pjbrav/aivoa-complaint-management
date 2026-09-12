import React from "react";
import { useDispatch } from "react-redux";
import { updateFieldLocally } from "../store/slices/complaintSlice";

/**
 * A single labeled input. Deliberately a controlled <input>, not a
 * read-only display of AI output — the human-in-the-loop requirement
 * means every extracted field must remain directly editable by the QA
 * reviewer at all times, not just via chat.
 */
export default function FormField({ field, label, value, confidence, placeholder, multiline = false, unit }) {
  const dispatch = useDispatch();

  const handleChange = (e) => {
    dispatch(updateFieldLocally({ field, value: e.target.value }));
  };

  const showConfidence = typeof confidence === "number";
  const isLow = showConfidence && confidence < 0.7;

  const inputProps = {
    id: field,
    value: value || "",
    onChange: handleChange,
    placeholder: placeholder || "Awaiting AI extraction...",
    className: `form-input${isLow ? " form-input-low-confidence" : ""}`,
  };

  return (
    <div className="form-field">
      <label htmlFor={field}>
        {label}
        {showConfidence && (
          <span className={`confidence-pill ${isLow ? "confidence-low" : "confidence-high"}`}>
            {Math.round(confidence * 100)}%
          </span>
        )}
      </label>
      {multiline ? (
        <textarea rows={3} {...inputProps} />
      ) : (
        <div className="form-input-wrapper">
          <input type="text" {...inputProps} />
          {unit && <span className="form-input-unit">{unit}</span>}
        </div>
      )}
    </div>
  );
}
