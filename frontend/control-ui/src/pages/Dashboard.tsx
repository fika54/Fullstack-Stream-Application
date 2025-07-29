import { useState } from "react";
import axios from "axios";
import PickChatter from "./Functions/PickChatter";

function Dashboard() {
    const [sessionId, setSessionId] = useState("stream1");

    
    const triggerGame = async (game: string) => {
        await axios.post(`http://localhost:8000/control/${sessionId}/${game}`);
    };

    const ws = new WebSocket("ws://localhost:8000/ws/test");
    ws.onmessage = (event) => {
        console.log("Received:", event.data);
    };

    return (
        <div className="p-4">
        <h1 className="text-xl font-bold">Control Panel</h1>
        <PickChatter />
        </div>
    );
}

export default Dashboard;