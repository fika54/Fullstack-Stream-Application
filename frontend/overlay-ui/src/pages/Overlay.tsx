import { useEffect, useState } from "react";

const Overlay = () => {
  const [game, setGame] = useState("");

  useEffect(() => {
    const socket = new WebSocket("ws://localhost:8000/ws/overlay/stream1");

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.action === "start_game") {
        setGame(data.game);
      }
    };
  }, []);

  return (
    <div className="text-white text-3xl p-4">
      {game === "guess_game" && <div>🎯 Guess the Number!</div>}
    </div>
  );
};

export default Overlay;