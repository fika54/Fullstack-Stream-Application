import { useState, useRef } from "react";
import "../FunctionStylesheet/PickChatter.css";

interface PickChatterProps {
    characterNumber: number;
}

const VOICE_STYLES = [
    'af', 'af_bella', 'af_nicole', 'af_sarah', 'af_sky',
    'am_adam', 'am_michael', 'bf_emma', 'bf_isabella',
    'bm_george', 'bm_lewis'
];

function PickChatter({ characterNumber }: PickChatterProps) {
    const [platform, setPlatform] = useState("either");
    const [pickedChatter, setPickedChatter] = useState<string | null>(null);
    const [manualChatter, setManualChatter] = useState<string>("");
    const [voiceStyle, setVoiceStyle] = useState<string>(VOICE_STYLES[0]);
    const wsPickRef = useRef<WebSocket | null>(null);
    const wsSetRef = useRef<WebSocket | null>(null);
    const wsResetRef = useRef<WebSocket | null>(null);
    const wsVoiceRef = useRef<WebSocket | null>(null);

    // Pick random chatter using websocket
    const pickRandomChatter = () => {
        if (wsPickRef.current) wsPickRef.current.close();
        const ws = new WebSocket("ws://localhost:8000/ws/pick_character");
        wsPickRef.current = ws;
        ws.onopen = () => {
            ws.send(JSON.stringify({ character_number: characterNumber, platform }));
        };
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setPickedChatter(data.username || "No chatter found");
            ws.close();
        };
        ws.onerror = () => {
            setPickedChatter("Error picking chatter");
            ws.close();
        };
    };

    // Set manual chatter using websocket
    const setManualPickedChatter = () => {
        if (!manualChatter.trim()) return;
        if (wsSetRef.current) wsSetRef.current.close();
        const ws = new WebSocket("ws://localhost:8000/ws/set_character");
        wsSetRef.current = ws;
        ws.onopen = () => {
            ws.send(JSON.stringify({ character_number: characterNumber, username: manualChatter, platform }));
        };
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setPickedChatter(data.username || "No chatter found");
            ws.close();
        };
        ws.onerror = () => {
            setPickedChatter("Error setting chatter");
            ws.close();
        };
        setManualChatter("");
    };

    // Reset chatter using websocket
    const resetChatter = () => {
        if (wsResetRef.current) wsResetRef.current.close();
        const ws = new WebSocket("ws://localhost:8000/ws/reset_character");
        wsResetRef.current = ws;
        ws.onopen = () => {
            ws.send(JSON.stringify({ character_number: characterNumber }));
        };
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (
                (characterNumber === 1 && data.status === "character_1_reset") ||
                (characterNumber === 2 && data.status === "character_2_reset")
            ) {
                setPickedChatter(null);
            }
            ws.close();
        };
        ws.onerror = () => {
            setPickedChatter("Error resetting chatter");
            ws.close();
        };
    };

    // Set voice style using websocket
    const setVoiceStyleWS = (style: string) => {
        setVoiceStyle(style);
        if (wsVoiceRef.current) wsVoiceRef.current.close();
        const ws = new WebSocket("ws://localhost:8000/ws/set_voice_style");
        wsVoiceRef.current = ws;
        ws.onopen = () => {
            ws.send(JSON.stringify({ character_number: characterNumber, voice_style: style }));
        };
        ws.onmessage = (event) => {
            // Optionally handle confirmation
            ws.close();
        };
        ws.onerror = () => {
            ws.close();
        };
    };

    return (
        <div className="pick-chatter-container">
            <h2 className="text-lg font-bold mb-2">Pick a Chatter</h2>
            <div className="pick-chatter-row">
                <label className="pick-chatter-label">Platform:</label>
                <select
                    value={platform}
                    onChange={e => setPlatform(e.target.value)}
                    className="pick-chatter-input"
                >
                    <option value="twitch">Twitch</option>
                    <option value="tiktok">TikTok</option>
                    <option value="either">Either</option>
                </select>
                <button onClick={pickRandomChatter} className="pick-chatter-btn">Pick Random</button>
            </div>
            <div className="pick-chatter-row">
                <label className="pick-chatter-label">Manual Pick:</label>
                <input
                    type="text"
                    value={manualChatter}
                    onChange={e => setManualChatter(e.target.value)}
                    className="pick-chatter-input"
                    placeholder="Enter username"
                />
                <button onClick={setManualPickedChatter} className="pick-chatter-btn">Set Chatter</button>
            </div>
            <div className="pick-chatter-row">
                <label className="pick-chatter-label">Voice Style:</label>
                <select
                    value={voiceStyle}
                    onChange={e => setVoiceStyleWS(e.target.value)}
                    className="pick-chatter-input"
                >
                    {VOICE_STYLES.map(style => (
                        <option key={style} value={style}>{style}</option>
                    ))}
                </select>
            </div>
            <div className="pick-chatter-row">
                <button onClick={resetChatter} className="pick-chatter-btn" style={{background: "#e11d48"}}>Reset Chatter</button>
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