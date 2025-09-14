import { useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import axios from "axios";

function App() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);

  const handlePrompt = async (e) => {
    if (e.key === "Enter" && e.target.value.trim() !== "") {
      const prompt = e.target.value;
      setLoading(true);
      try {
        // Automatically works on Hugging Face since frontend + backend are same host
        const res = await axios.post("/generate_events", { prompt });
        console.log("Backend response:", res.data);
        setEvents(res.data.events || []);
      } catch (err) {
        console.error("Error fetching events:", err);
        alert("Failed to fetch events. Check console for details.");
      }
      setLoading(false);
      e.target.value = "";
    }
  };

  return (
    <div style={{ maxWidth: "900px", margin: "40px auto" }}>
      <h1>📅 AI Calendar</h1>
      <input
        type="text"
        placeholder="Type something like 'Things to do in Valdosta GA' and press Enter"
        onKeyDown={handlePrompt}
        style={{ width: "100%", padding: "10px", marginBottom: "20px" }}
      />
      {loading && <p>Generating events...</p>}
      <FullCalendar
        plugins={[dayGridPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        events={events}
      />
    </div>
  );
}

export default App;
