import React, { FC, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Header from "./components/Header/Header";
import Status from "./components/Status/Status";
import RecordingButton from "./components/Recording/RecordingButtons";
import ChatContainer from "./components/ChatBox/ChatContainer";
import "./App.css";

type ChatMessage = { sender: string; message: string };

const WS_URL = "ws://localhost:8000/voice_stream";
const AUDIO_MIME = "audio/webm;codecs=opus";
const RECONNECT_BASE_MS = 500;
const RECONNECT_MAX_MS = 30000;

const App: FC = () => {
  const [statusMessage, setStatusMessage] = useState("Click to start recording");
  const [isRecording, setIsRecording] = useState(false);
  const [buttonDisabled, setButtonDisabled] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const intentionalCloseRef = useRef(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const recordedChunksRef = useRef<Blob[]>([]);

  const audioContextCtor = useMemo(() => {
    return (window.AudioContext || (window as any).webkitAudioContext) as
      | (new () => AudioContext)
      | undefined;
  }, []);

  const pushChatMessage = useCallback((msg: ChatMessage) => {
    setChatMessages((prev) => [...prev, msg]);
  }, []);

  const processAudioQueue = useCallback(async () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }

    const arrayBuffer = audioQueueRef.current.shift()!;
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new audioContextCtor!();
      }
      const ctx = audioContextRef.current;

      const audioBuffer: AudioBuffer = await new Promise((resolve, reject) => {
        ctx.decodeAudioData(
          arrayBuffer.slice(0),
          (buf) => resolve(buf),
          (err) => reject(err)
        );
      });

      const src = ctx.createBufferSource();
      src.buffer = audioBuffer;
      src.connect(ctx.destination);
      src.onended = () => processAudioQueue();
      src.start();
    } catch {
      setTimeout(processAudioQueue, 0);
    }
  }, [audioContextCtor]);

  const handleWsMessage = useCallback(
    (event: MessageEvent) => {
      if (event.data instanceof ArrayBuffer) {
        const arr = event.data;
        if (arr.byteLength > 0) {
          setButtonDisabled(true);
          audioQueueRef.current.push(arr);
          if (!isPlayingRef.current) {
            isPlayingRef.current = true;
            processAudioQueue();
          }
        }
        return;
      }

      if (typeof event.data === "string") {
        const text = event.data;
        const sepIndex = text.indexOf(":");
        const sender = sepIndex > -1 ? text.slice(0, sepIndex).trim() : "agent";
        const content = sepIndex > -1 ? text.slice(sepIndex + 1).trim() : text;
        pushChatMessage({ sender, message: content });

        if (sender.toLowerCase() === "agent") {
          setTimeout(() => {
            setButtonDisabled(false);
            setStatusMessage("Ready to talk");
          }, 400);
        }
      }
    },
    [processAudioQueue, pushChatMessage]
  );

  const connectWebSocket = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    if (reconnectTimerRef.current) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    const ws = new WebSocket(WS_URL);
    ws.binaryType = "arraybuffer";

    ws.addEventListener("open", () => {
      setStatusMessage("Ready to talk");
      setButtonDisabled(false);
      reconnectAttemptsRef.current = 0;
      intentionalCloseRef.current = false;
    });

    ws.addEventListener("message", handleWsMessage);

    ws.addEventListener("error", () => {
      setStatusMessage("WebSocket error occurred.");
      setButtonDisabled(true);
    });

    ws.addEventListener("close", () => {
      setButtonDisabled(true);
      setStatusMessage("Connection closed. Reconnecting...");

      if (intentionalCloseRef.current || document.hidden) return;

      reconnectAttemptsRef.current += 1;
      const delay = Math.min(
        RECONNECT_BASE_MS * 2 ** (reconnectAttemptsRef.current - 1),
        RECONNECT_MAX_MS
      );

      reconnectTimerRef.current = window.setTimeout(() => {
        reconnectTimerRef.current = null;
        connectWebSocket();
      }, delay);
    });

    wsRef.current = ws;
  }, [handleWsMessage]);

  const sendAudioData = useCallback(async (blob: Blob) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setStatusMessage("Connection lost. Please refresh.");
      setButtonDisabled(true);
      return;
    }
    const buffer = await blob.arrayBuffer();
    ws.send(buffer);
    setStatusMessage("Waiting for response...");
    isPlayingRef.current = false;
  }, []);

  const stopMediaStreamTracks = useCallback(() => {
    const stream = mediaStreamRef.current;
    if (!stream) return;
    stream.getTracks().forEach((t) => t.stop());
    mediaStreamRef.current = null;
  }, []);

  const startRecording = useCallback(async () => {
    setButtonDisabled(true);
    setStatusMessage("Requesting microphone...");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const options = MediaRecorder.isTypeSupported(AUDIO_MIME)
        ? { mimeType: AUDIO_MIME }
        : undefined;

      const mr = new MediaRecorder(stream, options as MediaRecorderOptions | undefined);
      recordedChunksRef.current = [];
      mediaRecorderRef.current = mr;

      mr.ondataavailable = (e: BlobEvent) => {
        if (e.data && e.data.size > 0) recordedChunksRef.current.push(e.data);
      };

      mr.onstop = () => {
        const blob = new Blob(recordedChunksRef.current, { type: options ? AUDIO_MIME : "audio/webm" });
        recordedChunksRef.current = [];
        sendAudioData(blob);
      };

      mr.start();
      setIsRecording(true);
      setStatusMessage("Recording...");
      setButtonDisabled(false);
    } catch (err: any) {
      setStatusMessage(err?.message ?? "Microphone access denied");
      setIsRecording(false);
      setButtonDisabled(false);
      stopMediaStreamTracks();
    }
  }, [sendAudioData, stopMediaStreamTracks]);

  const stopRecording = useCallback(() => {
    setIsRecording(false);
    setButtonDisabled(true);
    setStatusMessage("Processing...");
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    } else {
      stopMediaStreamTracks();
    }
  }, [stopMediaStreamTracks]);

  const handleToggleRecording = useCallback(async () => {
    if (!isRecording) {
      await startRecording();
    } else {
      stopRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  useEffect(() => {
    connectWebSocket();

    const handleUnload = () => {
      intentionalCloseRef.current = true;
      if (wsRef.current) {
        wsRef.current.close(1000, "unload");
      }
    };

    window.addEventListener("beforeunload", handleUnload);

    return () => {
      intentionalCloseRef.current = true;

      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
      }

      if (wsRef.current) {
        wsRef.current.close(1000, "cleanup");
        wsRef.current = null;
      }

      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }

      stopMediaStreamTracks();

      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }

      window.removeEventListener("beforeunload", handleUnload);
    };
  }, []);

  return (
    <div className="container">
      <div className="main-content">
        <Header />
        <Status message={statusMessage} />
        <RecordingButton
          onToggle={handleToggleRecording}
          isRecording={isRecording}
          disabled={buttonDisabled}
        />
      </div>

      <div className="chat-container">
        <ChatContainer chatMessages={chatMessages} />
      </div>
    </div>
  );
};

export default App;
