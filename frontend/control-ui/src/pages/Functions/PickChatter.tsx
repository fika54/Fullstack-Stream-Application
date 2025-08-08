import { useState, useRef } from "react";
import "../Stylesheet/PickChatter.css";

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
    const [alias, setAlias] = useState<string>("");
    const [message, setMessage] = useState<string>("");
    const wsPickRef = useRef<WebSocket | null>(null);
    const wsSetRef = useRef<WebSocket | null>(null);
    const wsResetRef = useRef<WebSocket | null>(null);
    const wsVoiceRef = useRef<WebSocket | null>(null);
    const wsCharacterMessageRef = useRef<WebSocket | null>(null);

    // Pick random chatter using websocket
    const pickRandomChatter = () => {
        if (!wsPickRef.current || wsPickRef.current.readyState === WebSocket.CLOSED) {
            const ws = new WebSocket("ws://localhost:8000/ws/pick_character");
            wsPickRef.current = ws;

            ws.onopen = () => {
                ws.send(JSON.stringify({ character_number: characterNumber, platform }));
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                setPickedChatter(data.username || "No chatter found");
            };

            ws.onerror = () => {
                setPickedChatter("Error picking chatter");
                ws.close();
            };

        } else if (wsPickRef.current.readyState === WebSocket.OPEN) {
            const ws = wsPickRef.current;
            ws.send(JSON.stringify({ character_number: characterNumber, platform }));

            ws.onerror = () => {
                setPickedChatter("Error picking chatter");
                ws.close();
            };
        }
    };

    // Set manual chatter using websocket
    const setManualPickedChatter = () => {
        if (!manualChatter.trim()) return;

        if (!wsSetRef.current || wsSetRef.current.readyState === WebSocket.CLOSED) {
            // Create new WebSocket connection
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

        } else if (wsSetRef.current.readyState === WebSocket.OPEN) {
            // Reuse existing connection
            const ws = wsSetRef.current;
            ws.send(JSON.stringify({ character_number: characterNumber, username: manualChatter, platform }));

            ws.onerror = () => {
                setPickedChatter("Error setting chatter");
                ws.close();
            };
        }

        setManualChatter("");
    };

    // Reset chatter using websocket
    const resetChatter = () => {
        // If websocket is not created or is closed, create a new one
        if (!wsResetRef.current || wsResetRef.current.readyState === WebSocket.CLOSED) {
            const ws = new WebSocket("ws://localhost:8000/ws/reset_character");
            wsResetRef.current = ws;

            ws.onopen = () => {
                ws.send(JSON.stringify({ character_number: characterNumber }));
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.status === `character_${characterNumber}_reset`) {
                    setPickedChatter(null);
                }
            };

            ws.onerror = () => {
                setPickedChatter("Error resetting chatter");
                ws.close();
            };

            ws.onclose = () => {
                wsResetRef.current = null;
            };

        } else {
            // Reuse the existing connection
            wsResetRef.current.send(JSON.stringify({ character_number: characterNumber }));
        }
    };

    // Set voice style using persistent/reusable websocket
    const setVoiceStyleWS = (style: string) => {
        setVoiceStyle(style);

        // If websocket is not created or is closed, create a new one
        if (!wsVoiceRef.current || wsVoiceRef.current.readyState >= WebSocket.CLOSING) {
            const ws = new WebSocket("ws://localhost:8000/ws/set_voice_style");
            wsVoiceRef.current = ws;

            ws.onopen = () => {
                ws.send(JSON.stringify({ character_number: characterNumber, voice_style: style }));
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.status === "ok") {
                    console.log(`Voice style for character ${characterNumber} set to ${style}`);
                } else if (data.status === "error") {
                    console.error(`Error setting voice style: ${data.detail}`);
                }
            };

            ws.onerror = () => {
                console.error("WebSocket error while setting voice style");
                ws.close();
            };

            ws.onclose = () => {
                wsVoiceRef.current = null; // Allow reconnecting next time
            };

        } else if (wsVoiceRef.current.readyState === WebSocket.OPEN) {
            // If connection is already open, just send the update
            wsVoiceRef.current.send(JSON.stringify({ character_number: characterNumber, voice_style: style }));
        }
    };

    const handle_message_as_character = () => {
        if (!alias.trim() || !message.trim()) return;

        if (!wsCharacterMessageRef.current || wsCharacterMessageRef.current.readyState === WebSocket.CLOSED) {
            const ws = new WebSocket("ws://localhost:8000/ws/message_as_character");
            wsCharacterMessageRef.current = ws;

            ws.onopen = () => {
                ws.send(JSON.stringify({ character_number: characterNumber, alias: alias, message: message }));
            };

            ws.onmessage = () => {
                setMessage("");
            };

            ws.onerror = () => {
                setPickedChatter("Error Sending Message");
                ws.close();
            };

        } else if (wsCharacterMessageRef.current.readyState === WebSocket.OPEN) {
            const ws = wsCharacterMessageRef.current;
            ws.send(JSON.stringify({ character_number: characterNumber, alias: alias, message: message }));

            ws.onerror = () => {
                setPickedChatter("Error Sending Message");
                ws.close();
            };
        }
    }

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

            {true && (
                <div className="pick-chatter-row">
                    <label className="pick-chatter-label">Alias:</label>
                    <input
                        type="text"
                        value={alias}
                        onChange={e => setAlias(e.target.value)}
                        className="pick-chatter-input"
                        placeholder="Set alias"
                    />
                    
                    <label className="pick-chatter-label">Message:</label>
                    <input
                        type="text"
                        value={message}
                        onChange={e => setMessage(e.target.value)}
                        className="pick-chatter-input"
                        placeholder="Message"
                    />
                    <button onClick={handle_message_as_character} className="pick-chatter-btn">Send Message</button>
                </div>
            )}
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