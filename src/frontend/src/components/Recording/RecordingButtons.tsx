// RecordingButton.tsx
import React from "react";
import "./RecordingButton.css";

interface RecordingButtonProps {
  onToggle: () => void;
  isRecording: boolean;
  disabled: boolean;
  className?: string;
}

const RecordingButton: React.FC<RecordingButtonProps> = ({
  onToggle,
  isRecording,
  disabled,
  className = "",
}) => {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      className={`fv-rec-btn ${isRecording ? "rec" : "idle"} ${
        disabled ? "disabled" : ""
      } ${className}`}
    >
      <span className="fv-icon-wrap">
        <span className={`mic-circle ${isRecording ? "pulse" : ""}`}></span>
        <span className="mic-icon">
          {isRecording ? (
            <svg viewBox="0 0 24 24" width="22" height="22" fill="#fff">
              <rect x="8" y="8" width="8" height="8" rx="2" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" width="22" height="22" fill="#fff">
              <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 14 0h-2z" />
            </svg>
          )}
        </span>
      </span>

      <span className="fv-text">
        {isRecording ? "Stop Recording" : "Start Recording"}
      </span>
    </button>
  );
};

export default RecordingButton;
