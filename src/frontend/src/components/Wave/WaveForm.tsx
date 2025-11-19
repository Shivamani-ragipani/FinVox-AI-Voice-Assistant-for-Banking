import React, { useState, useEffect, useRef, FC } from "react";
import "./WaveForm.css";

// --- Configuration Constants ---
const COLORS = {
  primary: "#2563eb",
  primaryLight: "#3b82f6",
  success: "#10b981",
  warning: "#f59e0b",
  error: "#ef4444",
  background: "#0f172a",
  surface: "#1e293b",
  surfaceLight: "#334155",
  text: "#f1f5f9",
  textSecondary: "#cbd5e1",
  divider: "#475569",
};

interface VoiceState {
  isListening: boolean;
  isProcessing: boolean;
  isIdle: boolean;
}

interface Message {
  text: string;
  isUser: boolean;
  timestamp: Date;
}

const BASE_HEIGHT_FACTORS: number[] = [0.3, 0.6, 0.8, 1.0, 0.9, 0.7, 0.5];
const MAX_BAR_PIXEL_HEIGHT = 100;
const BAR_WIDTH_PX = 6;
const ACTIVE_ANIMATION_INTERVAL_MS = 80;
const HEIGHT_VARIATION_RANGE = 0.5;
const MIN_RELATIVE_HEIGHT_FACTOR = 0.15;
const MAX_RELATIVE_HEIGHT_FACTOR = 1.3;

/**
 * Professional AI Voice Assistant UI Component
 * React + TypeScript with modern design and animations
 */
const Waveform: FC = () => {
  const [voiceState, setVoiceState] = useState<VoiceState>({
    isListening: false,
    isProcessing: false,
    isIdle: true,
  });

  const [currentHeightFactors, setCurrentHeightFactors] = useState<number[]>(
    BASE_HEIGHT_FACTORS
  );
  const [messages, setMessages] = useState<Message[]>([
    {
      text: "Hello! I'm your FinVox AI Assistant. How can I help you today?",
      isUser: false,
      timestamp: new Date(),
    },
  ]);
  const [transcription, setTranscription] = useState<string>("");
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Waveform animation
  useEffect(() => {
    if (!voiceState.isListening && !voiceState.isProcessing) {
      setCurrentHeightFactors(BASE_HEIGHT_FACTORS.map((f) => f * 0.3));
      return;
    }

    let lastUpdate = 0;

    const animate = (timestamp: number): void => {
      if (timestamp - lastUpdate > ACTIVE_ANIMATION_INTERVAL_MS) {
        setCurrentHeightFactors(
          BASE_HEIGHT_FACTORS.map((baseFactor) => {
            const variation = (Math.random() - 0.5) * HEIGHT_VARIATION_RANGE;
            const newFactor = baseFactor + variation * baseFactor;
            return Math.max(
              MIN_RELATIVE_HEIGHT_FACTOR,
              Math.min(MAX_RELATIVE_HEIGHT_FACTOR, newFactor)
            );
          })
        );
        lastUpdate = timestamp;
      }
      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animationFrameRef.current = requestAnimationFrame(animate);
    return () => {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [voiceState.isListening, voiceState.isProcessing]);

  const handleToggleMicrophone = (): void => {
    if (voiceState.isIdle) {
      setVoiceState({ isListening: true, isProcessing: false, isIdle: false });
      setTranscription("");
    } else if (voiceState.isListening) {
      setVoiceState({ isListening: false, isProcessing: true, isIdle: false });
    } else {
      setVoiceState({ isListening: false, isProcessing: false, isIdle: true });
      setTranscription("");
    }
  };

  const handleToggleMute = (): void => {
    setIsMuted(!isMuted);
  };

  const getStateColor = (): string => {
    if (voiceState.isListening) return COLORS.success;
    if (voiceState.isProcessing) return COLORS.warning;
    return COLORS.textSecondary;
  };

  const getStateLabel = (): string => {
    if (voiceState.isListening) return "Listening...";
    if (voiceState.isProcessing) return "Processing...";
    return "Ready";
  };

  return (
    <div className="waveform-container">
      {/* Main Chat Interface */}
      <div className="chat-interface">
        {/* Header */}
        <div className="interface-header">
          <div className="header-content">
            <div className="logo-section">
              <div className="logo">🎤</div>
              <div>
                <h1 className="app-title">FinVox AI</h1>
                <p className="app-subtitle">Voice Assistant</p>
              </div>
            </div>
            <div className="header-status">
              <div className="status-indicator" style={{ backgroundColor: getStateColor() }} />
              <span className="status-text">{getStateLabel()}</span>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="messages-area">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`message ${msg.isUser ? "user-message" : "ai-message"}`}
            >
              <div className="message-avatar">
                {msg.isUser ? "👤" : "🤖"}
              </div>
              <div className="message-bubble">
                <p className="message-text">{msg.text}</p>
                <span className="message-time">
                  {msg.timestamp.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Transcription Display */}
        {voiceState.isListening && transcription && (
          <div className="transcription-area">
            <p className="transcription-label">You:</p>
            <p className="transcription-text">{transcription}</p>
          </div>
        )}

        {/* Waveform Visualizer */}
        <div className="waveform-visualizer">
          <div
            className={`waveform ${
              voiceState.isListening ? "listening" : "idle"
            }`}
          >
            {currentHeightFactors.map((factor, index) => {
              const barPixelHeight = factor * MAX_BAR_PIXEL_HEIGHT;
              return (
                <div
                  key={index}
                  className="waveform-bar"
                  style={{
                    height: `${Math.max(4, barPixelHeight)}px`,
                    backgroundColor: voiceState.isListening
                      ? COLORS.primary
                      : COLORS.surfaceLight,
                    width: `${BAR_WIDTH_PX}px`,
                  }}
                />
              );
            })}
          </div>
        </div>

        {/* Control Buttons */}
        <div className="controls-area">
          <button
            className={`control-btn microphone-btn ${
              voiceState.isListening ? "active" : ""
            }`}
            onClick={handleToggleMicrophone}
            title={
              voiceState.isListening
                ? "Stop listening"
                : "Start listening"
            }
            aria-label="Toggle microphone"
          >
            <span className="btn-icon">
              {voiceState.isListening ? "🎤" : "🔇"}
            </span>
            <span className="btn-text">
              {voiceState.isListening ? "Listening" : "Speak"}
            </span>
          </button>

          <button
            className={`control-btn mute-btn ${isMuted ? "active" : ""}`}
            onClick={handleToggleMute}
            title={isMuted ? "Unmute" : "Mute"}
            aria-label="Toggle mute"
          >
            <span className="btn-icon">
              {isMuted ? "🔇" : "🔊"}
            </span>
            <span className="btn-text">{isMuted ? "Muted" : "Sound On"}</span>
          </button>

          <button
            className="control-btn clear-btn"
            onClick={() => setMessages([])}
            title="Clear conversation"
            aria-label="Clear conversation"
          >
            <span className="btn-icon">🗑️</span>
            <span className="btn-text">Clear</span>
          </button>
        </div>

        {/* Info Footer */}
        <div className="interface-footer">
          <p className="footer-text">
            {voiceState.isListening
              ? "Listening... Click to stop"
              : voiceState.isProcessing
              ? "Processing your request..."
              : "Click the microphone to start"}
          </p>
        </div>
      </div>
    </div>
  );
};

export default Waveform;
