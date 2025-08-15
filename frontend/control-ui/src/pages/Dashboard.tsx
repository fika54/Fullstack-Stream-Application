import { useState, useRef } from "react";
// import axios from "axios";
import PickChatter from "./Functions/PickChatter";
import { CratesWsController } from "./Functions/CratesController";
import "./Stylesheet/dashboard.css";

function Dashboard() {
    const [characterCount, setCharacterCount] = useState(2);
    const wsMuteRef = useRef<WebSocket | null>(null);
    const wsControlPollRef = useRef<WebSocket | null>(null); // New ref
    const wsControlDuelPollRef = useRef<WebSocket | null>(null); // New ref for duel poll
    const [muteStatus, setMuteStatus] = useState("unmuted");
    const [muted, setMuted] = useState(true);
    const [pollStatus, setPollStatus] = useState("hide");
    const wsShootGunRef = useRef<WebSocket | null>(null);
    const [gunStatus, setGunStatus] = useState("unfired");

    const ws = new WebSocket("ws://localhost:8000/ws/test");
    ws.onmessage = (event) => {
        console.log("Received:", event.data);
    };


    // Reset chatter using websocket
    const mute_tts = () => {
        // If websocket is not created or is closed, create a new one
        if (!wsMuteRef.current || wsMuteRef.current.readyState === WebSocket.CLOSED) {
            const ws = new WebSocket("ws://localhost:8000/ws/mute_tts");
            wsMuteRef.current = ws;

            ws.onopen = () => {
                ws.send(JSON.stringify({ mute: muted }));
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                setMuteStatus(data.status);
            };

            ws.onerror = () => {
                setMuteStatus("Error muting TTS");
                ws.close();
            };
 
            ws.onclose = () => {
                wsMuteRef.current = null;
            };

        } else {
            // Reuse the existing connection
            wsMuteRef.current.send(JSON.stringify({ mute: muted }));
        }
    };

    // Reset chatter using websocket
    const shoot_gun = (command: "shoot" | "flip" | "hide") => {
        // If websocket is not created or is closed, create a new one
        if (!wsShootGunRef.current || wsShootGunRef.current.readyState === WebSocket.CLOSED) {
            const ws = new WebSocket("ws://localhost:8000/ws/shoot_gun");
            wsShootGunRef.current = ws;

            ws.onopen = () => {
                ws.send(JSON.stringify({ gun: "shoot the gun!" , command: command }));
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                setGunStatus(data.status);
            };

            ws.onerror = () => {
                setGunStatus("Error shooting gun");
                ws.close();
            };
 
            ws.onclose = () => {
                wsShootGunRef.current = null;
            };

        } else {
            // Reuse the existing connection
            wsShootGunRef.current.send(JSON.stringify({ command: command }));
        }
    };

    // Start or end poll via WebSocket
    const sendPollCommand = (command: "start" | "end" | "hide") => {
        if (!wsControlPollRef.current || wsControlPollRef.current.readyState === WebSocket.CLOSED) {
            const ws = new WebSocket("ws://localhost:8000/ws/control_poll");
            wsControlPollRef.current = ws;

            ws.onopen = () => {
                ws.send(JSON.stringify({ poll: command }));
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                setPollStatus(data.status);
            };

            ws.onerror = () => {
                console.error("Poll WebSocket error");
                ws.close();
            };

            ws.onclose = () => {
                wsControlPollRef.current = null;
            };
        } else {
            wsControlPollRef.current.send(JSON.stringify({ poll: command }));
        }
    };

    // Start or end poll via WebSocket
    const sendDuelCommand = (command: "start" | "end" | "hide") => {
        if (!wsControlDuelPollRef.current || wsControlDuelPollRef.current.readyState === WebSocket.CLOSED) {
            const ws = new WebSocket("ws://localhost:8000/ws/control_duel_poll");
            wsControlDuelPollRef.current = ws;

            ws.onopen = () => {
                ws.send(JSON.stringify({ poll: command }));
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                setPollStatus(data.status);
            };

            ws.onerror = () => {
                console.error("Poll WebSocket error");
                ws.close();
            };

            ws.onclose = () => {
                wsControlDuelPollRef.current = null;
            };
        } else {
            wsControlDuelPollRef.current.send(JSON.stringify({ poll: command }));
        }
    };

    const handleAdd = () => {
        setCharacterCount((prev) => prev + 1);
    };

    const handleRemove = () => {
        setCharacterCount((prev) => (prev > 1 ? prev - 1 : 1));
    };

    const handleMuteToggle = () => {
        setMuted((prev) => !prev);
        mute_tts();
    }

    return (
        <div className="dashboard-container">
            <h1 className="dashboard-title">Control Panel</h1>
            <div className="dashboard-controls">
                <button onClick={handleAdd} className="dashboard-btn add">Add</button>
                <button onClick={handleRemove} className="dashboard-btn remove">Remove</button>
                <button onClick={handleMuteToggle} className="dashboard-btn remove">Toggle tts</button>
            </div>
            <div className="dashboard-status">
                <p>Mute Status: {muteStatus}</p>
                <p>Characters added: {characterCount}</p>
                <p>Poll Status: {pollStatus}</p>
                <p>Gun Status: {gunStatus}</p>
            </div>
            <div className="character-list">
                {[...Array(characterCount)].map((_, idx) => (
                    <div className="character-card" key={idx + 1}>
                        <h2>Character {idx + 1}</h2>
                        <PickChatter characterNumber={idx + 1} />
                    </div>
                ))}
            </div>
            <div className="dashboard-footer">
                <CratesWsController
                    wsUrl="ws://localhost:8000/ws/crates"   // <-- change to your WS route
                    // protocols={["your-subprotocol-if-any"]} // optional
                    // autoReconnect={true}                    // optional (default true)
                />
            </div>

            <div className="dashboard-footer">
                <button onClick={() => sendPollCommand("start")} className="dashboard-btn start">Start Poll</button>
                <button onClick={() => sendPollCommand("end")} className="dashboard-btn end">End Poll</button>
                <button onClick={() => sendPollCommand("hide")} className="dashboard-btn end">Hide Poll</button>
            </div>
            <div className="dashboard-footer">
                <button onClick={() => sendDuelCommand("start")} className="dashboard-btn start">Start duel</button>
                <button onClick={() => sendDuelCommand("end")} className="dashboard-btn end">End duel</button>
                <button onClick={() => sendDuelCommand("hide")} className="dashboard-btn end">Hide duel</button>
            </div>
            <div className="dashboard-footer">
                <button onClick={() => shoot_gun("shoot")} className="dashboard-btn remove">Shoot Gun</button>
                <button onClick={() => shoot_gun("flip")} className="dashboard-btn add">flip Gun</button>
                <button onClick={() => shoot_gun("hide")} className="dashboard-btn remove">hide Gun</button>
            </div>
        </div>
    );
}

export default Dashboard;