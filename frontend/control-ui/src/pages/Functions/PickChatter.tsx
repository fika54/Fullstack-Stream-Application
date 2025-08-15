import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "../Stylesheet/PickChatter.css";

interface PickChatterProps {
  characterNumber: number;
}

const VOICE_STYLES = [
  "af", "af_bella", "af_nicole", "af_sarah", "af_sky",
  "am_adam", "am_michael", "bf_emma", "bf_isabella",
  "bm_george", "bm_lewis",
] as const;

type Loading = false | "pick" | "set" | "reset" | "voice" | "send";
type ConnState = "connecting" | "open" | "closed";

function PickChatter({ characterNumber }: PickChatterProps) {
  const [platform, setPlatform] = useState("either");
  const [pickedChatter, setPickedChatter] = useState<string | null>(null);
  const [manualChatter, setManualChatter] = useState<string>("");
  const [voiceStyle, setVoiceStyle] = useState<string>(VOICE_STYLES[0]);
  const [alias, setAlias] = useState<string>("");
  const [message, setMessage] = useState<string>("");

  const [loading, setLoading] = useState<Loading>(false);
  const [connState, setConnState] = useState<ConnState>("connecting");

  // Persistent socket + helpers
  const wsRef = useRef<WebSocket | null>(null);
  const queueRef = useRef<any[]>([]); // outbound message queue until OPEN
  const reconnectTimer = useRef<number | null>(null);
  const retriesRef = useRef(0);
  const mounted = useRef(true);

  // Failsafe: clear loading if no response arrives in time
  const clearLoadingTimer = useRef<number | null>(null);
  const armClearLoading = useCallback((ms = 6000) => {
    if (clearLoadingTimer.current) window.clearTimeout(clearLoadingTimer.current);
    clearLoadingTimer.current = window.setTimeout(() => {
      setLoading(false);
      clearLoadingTimer.current = null;
    }, ms);
  }, []);
  const disarmClearLoading = useCallback(() => {
    if (clearLoadingTimer.current) {
      window.clearTimeout(clearLoadingTimer.current);
      clearLoadingTimer.current = null;
    }
  }, []);

  // ---- Single control channel URL with character in query ----
  const wsUrl = useMemo(
    () => `ws://localhost:8000/ws/character_control?character=${encodeURIComponent(
      String(characterNumber)
    )}`,
    [characterNumber]
  );

  // Basic sender with queueing
  const send = useCallback((msg: any) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
      return true;
    }
    queueRef.current.push(msg);
    return false;
  }, []);

  const flushQueue = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    while (queueRef.current.length) {
      ws.send(JSON.stringify(queueRef.current.shift()));
    }
  }, []);

  // Auto-reconnect with capped backoff
  const scheduleReconnect = useCallback(() => {
    if (!mounted.current) return;
    if (reconnectTimer.current) return;
    const attempt = (retriesRef.current += 1);
    const delay = Math.min(5000, 500 * Math.pow(1.6, attempt - 1)); // up to 5s
    reconnectTimer.current = window.setTimeout(() => {
      reconnectTimer.current = null;
      connect();
    }, delay);
  }, []);

  const connect = useCallback(() => {
    try {
      setConnState("connecting");
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        retriesRef.current = 0;
        setConnState("open");
        flushQueue();
        // Optionally fetch current state:
        // send({ type: "character:status:get" });
      };

      ws.onmessage = (ev) => {
        let data: any = ev.data;
        try {
          data = JSON.parse(ev.data);
        } catch {
          return; // ignore non-JSON
        }

        // 1) Update picked chatter if present
        const uname = data?.username ?? data?.user ?? data?.name;
        if (typeof uname === "string" && uname.trim()) {
          setPickedChatter(uname);
        }

        // 2) Reset acknowledgement
        if (
          typeof data?.status === "string" &&
          (data.status === `character_${characterNumber}_reset` || /reset/i.test(data.status))
        ) {
          setPickedChatter(null);
        }

        // 3) Decide if this message completes an action -> clear loading
        const hasStatus = typeof data?.status === "string";
        const hasType = typeof data?.type === "string";
        const isOkOrErr = hasType && (data.type === "ok" || data.type === "error");
        const isCharacterEvent = hasType && data.type.startsWith("character:");
        const hasUsername = typeof uname === "string" && uname.trim().length > 0;

        if (isOkOrErr || isCharacterEvent || hasStatus || hasUsername) {
          setLoading(false);
          disarmClearLoading();
        }
      };

      ws.onclose = () => {
        setConnState("closed");
        setLoading(false);
        disarmClearLoading();
        scheduleReconnect();
      };

      ws.onerror = () => {
        setLoading(false);
        disarmClearLoading();
      };
    } catch {
      setConnState("closed");
      scheduleReconnect();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsUrl, flushQueue, scheduleReconnect, disarmClearLoading]);

  useEffect(() => {
    mounted.current = true;
    connect();
    return () => {
      mounted.current = false;
      if (reconnectTimer.current) window.clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
      if (clearLoadingTimer.current) window.clearTimeout(clearLoadingTimer.current);
      clearLoadingTimer.current = null;
      try {
        wsRef.current?.close();
      } catch {}
      wsRef.current = null;
    };
  }, [connect]);

  const connected = connState === "open";
  const disabled = !connected || !!loading;

  // ---------------- Actions ----------------
  const pickRandomChatter = useCallback(() => {
    if (disabled) return;
    setLoading("pick");
    armClearLoading(); // failsafe
    send({ type: "character:pick", character_number: characterNumber, platform });
  }, [disabled, send, characterNumber, platform, armClearLoading]);

  const setManualPickedChatter = useCallback(() => {
    const name = manualChatter.trim();
    if (disabled || !name) return;
    setLoading("set");
    armClearLoading();
    send({
      type: "character:set",
      character_number: characterNumber,
      username: name,
      platform,
    });
    setManualChatter("");
  }, [disabled, manualChatter, send, characterNumber, platform, armClearLoading]);

  const resetChatter = useCallback(() => {
    if (disabled) return;
    setLoading("reset");
    armClearLoading();
    send({ type: "character:reset", character_number: characterNumber });
  }, [disabled, send, characterNumber, armClearLoading]);

  const setVoiceStyleWS = useCallback(
    (style: string) => {
      setVoiceStyle(style); // optimistic UI
      if (!connected) return;
      setLoading("voice");
      armClearLoading();
      send({ type: "character:voice", character_number: characterNumber, voice_style: style });
    },
    [connected, send, characterNumber, armClearLoading]
  );

  const handle_message_as_character = useCallback(() => {
    const a = alias.trim();
    const m = message.trim();
    if (disabled || !a || !m) return;
    setLoading("send");
    armClearLoading();
    send({ type: "character:message", character_number: characterNumber, alias: a, message: m });
    setMessage(""); // optimistic clear; remove if you prefer to wait for ack
  }, [disabled, alias, message, send, characterNumber, armClearLoading]);

  // ----------------------------------------------------------------------

  return (
    <div className="pick-chatter-container">
      <h2 className="text-lg font-bold mb-2">Pick a Chatter</h2>

      {/* Connection badge */}
      <div style={{ marginBottom: 8 }}>
        <span
          className={`text-xs px-2 py-1 rounded ${
            connected ? "bg-green-100 text-green-700" : connState === "connecting" ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-700"
          }`}
        >
          {connected ? "WS: Connected" : connState === "connecting" ? "WS: Connecting…" : "WS: Disconnected"}
        </span>
      </div>

      <div className="pick-chatter-row">
        <label className="pick-chatter-label">Platform:</label>
        <select
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
          className="pick-chatter-input"
          disabled={disabled}
        >
          <option value="twitch">Twitch</option>
          <option value="tiktok">TikTok</option>
          <option value="either">Either</option>
        </select>
        <button onClick={pickRandomChatter} className="pick-chatter-btn" disabled={disabled}>
          {loading === "pick" ? "Picking…" : "Pick Random"}
        </button>
      </div>

      <div className="pick-chatter-row">
        <label className="pick-chatter-label">Manual Pick:</label>
        <input
          type="text"
          value={manualChatter}
          onChange={(e) => setManualChatter(e.target.value)}
          className="pick-chatter-input"
          placeholder="Enter username"
          disabled={disabled}
        />
        <button onClick={setManualPickedChatter} className="pick-chatter-btn" disabled={disabled || !manualChatter.trim()}>
          {loading === "set" ? "Setting…" : "Set Chatter"}
        </button>
      </div>

      <div className="pick-chatter-row">
        <label className="pick-chatter-label">Voice Style:</label>
        <select
          value={voiceStyle}
          onChange={(e) => setVoiceStyleWS(e.target.value)}
          className="pick-chatter-input"
          disabled={!connected || loading === "voice"}
        >
          {VOICE_STYLES.map((style) => (
            <option key={style} value={style}>
              {style}
            </option>
          ))}
        </select>
      </div>

      <div className="pick-chatter-row">
        <label className="pick-chatter-label">Alias:</label>
        <input
          type="text"
          value={alias}
          onChange={(e) => setAlias(e.target.value)}
          className="pick-chatter-input"
          placeholder="Set alias"
          disabled={disabled}
        />

        <label className="pick-chatter-label">Message:</label>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className="pick-chatter-input"
          placeholder="Message"
          disabled={disabled}
        />
        <button onClick={handle_message_as_character} className="pick-chatter-btn" disabled={disabled || !alias.trim() || !message.trim()}>
          {loading === "send" ? "Sending…" : "Send Message"}
        </button>
      </div>

      <div className="pick-chatter-row">
        <button
          onClick={resetChatter}
          className="pick-chatter-btn"
          style={{ background: "#e11d48" }}
          disabled={disabled}
        >
          {loading === "reset" ? "Resetting…" : "Reset Chatter"}
        </button>
      </div>

      {pickedChatter && (
        <div className="mt-2">
          <strong>Picked Chatter:</strong> {pickedChatter}
        </div>
      )}
    </div>
  );
}

export default PickChatter;
