import { useState, useRef } from "react";
// import axios from "axios";
import PickChatter from "./Functions/PickChatter";
import "./Stylesheet/dashboard.css";

function Dashboard() {
    const [characterCount, setCharacterCount] = useState(2);
    const wsMuteRef = useRef<WebSocket | null>(null);
    const wsControlPollRef = useRef<WebSocket | null>(null); // New ref
    const [muteStatus, setMuteStatus] = useState("unmuted");
    const [muted, setMuted] = useState(true);
    const [pollStatus, setPollStatus] = useState("hide");

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
                <button onClick={() => sendPollCommand("start")} className="dashboard-btn start">Start Poll</button>
                <button onClick={() => sendPollCommand("end")} className="dashboard-btn end">End Poll</button>
                <button onClick={() => sendPollCommand("hide")} className="dashboard-btn end">Hide Poll</button>
            </div>
            <div className="dashboard-status">
                <p>Mute Status: {muteStatus}</p>
                <p>Characters added: {characterCount}</p>
                <p>Poll Status: {pollStatus}</p>
            </div>
            <div className="character-list">
                {[...Array(characterCount)].map((_, idx) => (
                    <div className="character-card" key={idx + 1}>
                        <h2>Character {idx + 1}</h2>
                        <PickChatter characterNumber={idx + 1} />
                    </div>
                ))}
            </div>
        </div>
    );
}

export default Dashboard;