import { useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import axios from "axios";

function App() {
  const [events, setEvents] = useState([]);

  const handlePrompt = async (prompt) => {
    try {
      const res = await axios.post("http://localhost:8000/generate_events", {
        prompt,
      });
      setEvents(res.data.events);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ maxWidth: "900px", margin: "40px auto" }}>
      <h1>AI Calendar</h1>
      <input
        type="text"
        placeholder="Describe events..."
        onKeyDown={(e) => {
          if (e.key === "Enter") handlePrompt(e.target.value);
        }}
        style={{ width: "100%", padding: "10px", marginBottom: "20px" }}
      />
      <FullCalendar
        plugins={[dayGridPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        events={events}
      />
    </div>
  );
}

export default App;
