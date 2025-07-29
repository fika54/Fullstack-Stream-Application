import { useState } from "react";
import axios from "axios";
import "../FunctionStylesheet/PickChatter.css";

function PickChatter() {
    const [platform, setPlatform] = useState("either");
    const [pickedChatter, setPickedChatter] = useState<string | null>(null);
    const [manualChatter, setManualChatter] = useState<string>("");

    const pickRandomChatter = async () => {
        try {
            const res = await axios.get(`http://localhost:8000/pick_random/${platform}`);
            setPickedChatter(res.data.chatter || "No chatter found");
        } catch {
            setPickedChatter("Error picking chatter");
        }
    };

    const setManualPickedChatter = async () => {
        if (!manualChatter.trim()) return;
        setPickedChatter(manualChatter);
        await axios.post("http://localhost:8000/set_picked_chatter", {
            platform,
            chatter: manualChatter
        });
        setManualChatter("");
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
            {pickedChatter && (
                <div className="mt-2">
                    <strong>Picked Chatter:</strong> {pickedChatter}
                </div>
            )}
        </div>
    );
}

export default PickChatter;