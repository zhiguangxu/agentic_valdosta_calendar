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

  const fetchEvents = async () => {
    const query = "Things to do in Valdosta GA";
    setLoading(true);
    try {
      const res = await axios.post("/generate_events", { query });
      console.log("Backend response:", res.data);
      setEvents(res.data.events || []);
    } catch (err) {
      console.error("Error fetching events:", err);
      alert("Failed to fetch events. Check console for details.");
    }
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: "900px", margin: "40px auto" }}>
      <h1>🗺️ Wonder what to do in Valdosta GA?</h1>
      <button
        onClick={fetchEvents}
        style={{
          padding: "10px 20px",
          fontSize: "16px",
          marginBottom: "20px",
          cursor: "pointer",
        }}
      >
        Let's find out!
      </button>

      {loading && <p>Generating events...</p>}

      <FullCalendar
        plugins={[dayGridPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        events={events}
        eventClick={(info) => {
          if (info.event.url) {
            window.open(info.event.url, "_blank");
            info.jsEvent.preventDefault();
          }
        }}
        eventDidMount={(info) => {
          const desc = info.event.extendedProps.description || "No description";
          const url = info.event.url
            ? `<a href="${info.event.url}" target="_blank" rel="noopener noreferrer">More info</a>`
            : "";
          tippy(info.el, {
            content: `<strong>${info.event.title}</strong><br>${desc}<br>${url}`,
            allowHTML: true,
          });
        }}
      />
    </div>
  );
}

export default App;
