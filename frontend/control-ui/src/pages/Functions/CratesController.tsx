import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

/**
 * Minimal message protocol (adjust to your backend):
 *  -> { type: "crates:start" }
 *  -> { type: "crates:select", crate: number }   // 1..12
 *  -> { type: "crates:reset" }
 *
 * Server can reply with any of:
 *  <- { type: "ok", message?: string }
 *  <- { type: "error", message: string }
 *  <- { type: "crates:status", active: boolean, opened?: number[], message?: string }
 *  <- { type: "crates:result", message: string, active?: boolean, opened?: number[] }
 */

type CratesWsControllerProps = {
  /** ws://host:port/path or wss://... */
  wsUrl: string;
  /** Optional subprotocols, if your server requires (leave empty for vanilla ws). */
  protocols?: string | string[];
  /** Optional: disable auto-reconnect */
  autoReconnect?: boolean;
};

type Incoming =
  | { type: "ok"; message?: string }
  | { type: "error"; message: string }
  | { type: "crates:status"; active: boolean; opened?: number[]; message?: string }
  | { type: "crates:result"; message: string; active?: boolean; opened?: number[] } 

const MAX_LOG = 50;

const ready = (ws?: WebSocket | null) => ws && ws.readyState === WebSocket.OPEN;

export const CratesWsController: React.FC<CratesWsControllerProps> = ({
  wsUrl,
  protocols,
  autoReconnect = true,
}) => {
  const [gameActive, setGameActive] = useState<boolean | null>(null);
  const [opened, setOpened] = useState<number[]>([]);
  const [lastMessage, setLastMessage] = useState<string>("");
  const [loading, setLoading] = useState<false | "start" | "select" | "reset">(false);
  const [crateInput, setCrateInput] = useState("1");

  const [connState, setConnState] = useState<"connecting" | "open" | "closed">("connecting");
  const [retries, setRetries] = useState(0);
  const [log, setLog] = useState<Array<{ id: string; ts: number; text: string }>>([]);
  const logSeq = useRef(0);

  const wsRef = useRef<WebSocket | null>(null);
  const queueRef = useRef<any[]>([]); // queue outbound messages until socket is open
  const reconnectTimer = useRef<number | null>(null);

  const addLog = useCallback((text: string) => {
    const ts = Date.now();
    const id = `${ts}-${++logSeq.current}`; // unique per entry
    setLog(prev => [{ id, ts, text }, ...prev].slice(0, 50));
  }, []);

  const flushQueue = useCallback(() => {
    const ws = wsRef.current;
    if (!ready(ws)) return;
    while (queueRef.current.length) {
      const msg = queueRef.current.shift();
      ws!.send(JSON.stringify(msg));
    }
  }, []);

  const send = useCallback((msg: any) => {
    const ws = wsRef.current;
    if (!ready(ws)) {
      queueRef.current.push(msg);
      return false;
    }
    ws!.send(JSON.stringify(msg));
    return true;
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (!autoReconnect) return;
    if (reconnectTimer.current) return;
    const attempt = retries + 1;
    const delay = Math.min(5000, 500 * Math.pow(1.6, attempt - 1)); // backoff to 5s max
    reconnectTimer.current = window.setTimeout(() => {
      reconnectTimer.current = null;
      setRetries(attempt);
      connect();
    }, delay);
  }, [autoReconnect, retries]);

  const connect = useCallback(() => {
    try {
      setConnState("connecting");
      const ws = new WebSocket(wsUrl, protocols);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnState("open");
        setRetries(0);
        addLog("🔌 WebSocket connected");
        flushQueue();
        // Ask for current status (optional; if your server pushes status on join, you can skip)
        send({ type: "crates:status:get" });
      };

      ws.onmessage = (ev) => {
        let data: Incoming;
        try {
          data = JSON.parse(ev.data);
        } catch {
          addLog(`📩 ${ev.data}`);
          setLastMessage(String(ev.data));
          return;
        }

        switch (data.type) {
          case "ok":
            if (data.message) {
              addLog(`✅ ${data.message}`);
              setLastMessage(data.message);
            }
            break;

          case "error":
            addLog(`❌ ${data.message}`);
            setLastMessage(data.message);
            setLoading(false);
            break;

          case "crates:status":
            setGameActive(data.active);
            setOpened(data.opened ?? []);
            if (data.message) setLastMessage(data.message);
            addLog(`ℹ️ Status: ${data.active ? "active" : "inactive"}`);
            setLoading(false);
            break;

          case "crates:result":
            if (typeof data.active === "boolean") setGameActive(data.active);
            if (data.opened) setOpened(data.opened);
            setLastMessage(data.message);
            addLog(`🎯 ${data.message}`);
            setLoading(false);
            break;

          default:
            addLog(`📨 ${JSON.stringify(data)}`);
            break;
        }
      };

      ws.onclose = () => {
        setConnState("closed");
        addLog("🔌 WebSocket closed");
        setLoading(false);
        scheduleReconnect();
      };

      ws.onerror = () => {
        addLog("⚠️ WebSocket error");
      };
    } catch (e: any) {
      addLog(`⚠️ Connect error: ${e?.message ?? e}`);
      setConnState("closed");
      scheduleReconnect();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsUrl, protocols]); // note: scheduleReconnect not included to avoid stale timer reuse

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) window.clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
      wsRef.current?.close();
    };
  }, [connect]);

  // Actions
  const startGame = useCallback(() => {
    setLoading("start");
    send({ type: "crates:start" });
  }, [send]);

  const resetGame = useCallback(() => {
    setLoading("reset");
    send({ type: "crates:reset" });
  }, [send]);

  const selectCrate = useCallback(
    (n?: number) => {
      const num = Number(n ?? crateInput);
      if (!Number.isInteger(num) || num < 1 || num > 12) {
        const msg = "Please choose a crate number between 1 and 12.";
        setLastMessage(msg);
        addLog(`⚠️ ${msg}`);
        return;
      }
      setLoading("select");
      send({ type: "crates:select", crate: num });
    },
    [crateInput, send, addLog]
  );

  const disabled = loading !== false || connState !== "open";

  const statusBadge = useMemo(() => {
    const cls =
      connState === "open"
        ? "bg-green-100 text-green-700"
        : connState === "connecting"
        ? "bg-yellow-100 text-yellow-800"
        : "bg-red-100 text-red-700";
    return (
      <span className={`text-xs px-2 py-1 rounded ${cls}`}>
        {connState === "open" ? "WS: Connected" : connState === "connecting" ? "WS: Connecting…" : "WS: Disconnected"}
      </span>
    );
  }, [connState]);

  // Simple helper to indicate opened crates (if server sends that list)
  const isOpened = useCallback((n: number) => opened.includes(n), [opened]);

  return (
    <div className="max-w-xl mx-auto p-4 rounded-2xl shadow border">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xl font-semibold">Crates Game Controller (WebSocket)</h2>
        {statusBadge}
      </div>

      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={startGame}
          disabled={disabled}
          className="px-3 py-2 rounded-lg border hover:bg-gray-50 disabled:opacity-50"
          aria-busy={loading === "start"}
        >
          {loading === "start" ? "Starting…" : "Start Game"}
        </button>
        <button
          onClick={resetGame}
          disabled={disabled}
          className="px-3 py-2 rounded-lg border hover:bg-gray-50 disabled:opacity-50"
          aria-busy={loading === "reset"}
        >
          {loading === "reset" ? "Resetting…" : "Reset Game"}
        </button>

        <span
          className={`ml-auto text-sm px-2 py-1 rounded ${
            gameActive ? "bg-green-100 text-green-700" : gameActive === null ? "bg-gray-100 text-gray-600" : "bg-red-100 text-red-700"
          }`}
          aria-live="polite"
        >
          {gameActive === null ? "Status: Unknown" : gameActive ? "Status: Active" : "Status: Inactive"}
        </span>
      </div>

      {/* Manual input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          selectCrate();
        }}
        className="mb-3"
      >
        <label htmlFor="crate-input" className="block text-sm font-medium mb-1">
          Crate number (1–12)
        </label>
        <div className="flex gap-2">
          <input
            id="crate-input"
            type="number"
            min={1}
            max={12}
            value={crateInput}
            onChange={(e) => setCrateInput(e.target.value)}
            className="w-28 px-3 py-2 rounded-lg border"
            disabled={disabled}
          />
          <button
            type="submit"
            disabled={disabled}
            className="px-3 py-2 rounded-lg border hover:bg-gray-50 disabled:opacity-50"
            aria-busy={loading === "select"}
          >
            {loading === "select" ? "Selecting…" : "Select Crate"}
          </button>
        </div>
      </form>

      {/* Number pad */}
      <div className="mb-4">
        <div className="text-sm font-medium mb-2">Quick Select</div>
        <div className="grid grid-cols-4 gap-2">
          {Array.from({ length: 12 }, (_, i) => i + 1).map((n) => {
            const openedCls = isOpened(n) ? "opacity-40 line-through" : "";
            return (
              <button
                key={n}
                type="button"
                onClick={() => selectCrate(n)}
                disabled={disabled || isOpened(n)}
                aria-label={`Select crate ${n}`}
                className={`py-3 rounded-lg border hover:bg-gray-50 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${openedCls}`}
                title={isOpened(n) ? "Already opened" : `Select crate ${n}`}
              >
                {n}
              </button>
            );
          })}
        </div>
        <p className="text-xs text-gray-500 mt-2">Click a number to select that crate immediately.</p>
      </div>

      {lastMessage && (
        <div className="mb-3 rounded-lg border p-3 bg-gray-50" role="status" aria-live="polite">
          <div className="text-sm">{lastMessage}</div>
        </div>
      )}

      <details>
        <summary className="cursor-pointer text-sm text-gray-700">Event Log</summary>
        <ul className="mt-2 space-y-1 text-sm">
          {log.map(item => (
            <li key={item.id} className="font-mono">
              {new Date(item.ts).toLocaleTimeString()} — {item.text}
            </li>
          ))}
          {log.length === 0 && <li className="text-gray-500">No events yet.</li>}
        </ul>
      </details>
    </div>
  );
};

export default CratesWsController;
