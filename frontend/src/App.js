import React, { useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import tippy from "tippy.js";
import "tippy.js/dist/tippy.css";

import axios from "axios";

function App() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);

  const handlePrompt = async (e) => {
    if (e.key === "Enter" && e.target.value.trim() !== "") {
      const query = e.target.value.trim();
      setLoading(true);
      try {
        // Send JSON body with 'query' key
        const res = await axios.post("/generate_events", { query });

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
      <h1>🗓️ Agentic Event Calendar (v0.3)</h1>
      <input
        type="text"
        placeholder="Type something like 'Things to do' and press Enter"
        onKeyDown={handlePrompt}
        style={{ width: "100%", padding: "10px", marginBottom: "20px" }}
      />
      {loading && <p>Generating events...</p>}
      <FullCalendar
        plugins={[dayGridPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        events={events}
        eventClick={(info) => {
          if (info.event.url) {
            window.open(info.event.url, "_blank");
            info.jsEvent.preventDefault(); // prevents default navigation
          }
        }}
        eventDidMount={(info) => {
          // Attach tooltip with description + link
          tippy(info.el, {
            content: `
              <strong>${info.event.title}</strong><br>
              ${info.event.extendedProps.description}<br>
              <a href="${info.event.url}" target="_blank" rel="noopener noreferrer">More info</a>
            `,
            allowHTML: true,
          });
        }}
      />
    </div>
  );
}

export default App;
