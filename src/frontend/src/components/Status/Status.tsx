// Status.tsx
import React from "react";
import "./Status.css";

interface StatusProps {
  message?: string;
}

const Status: React.FC<StatusProps> = ({ message }) => {
  if (!message) return null;

  return (
    <div className="fv-status-wrap">
      <div className="fv-status-pill">
        <span className="fv-status-dot" />
        <span className="fv-status-msg">{message}</span>
      </div>
    </div>
  );
};

export default Status;
