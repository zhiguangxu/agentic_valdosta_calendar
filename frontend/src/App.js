// frontend/App.js
import React, { useState, useEffect } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import tippy from "tippy.js";
import "tippy.js/dist/tippy.css";
import axios from "axios";

function App() {
  const [events, setEvents] = useState([]);
  const [attractions, setAttractions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [sortBy, setSortBy] = useState("name");
  const [activeTab, setActiveTab] = useState("events");
  const attractionsPerPage = 6;

  const fetchEvents = async () => {
    setLoading(true);
    setCurrentPage(1); // Reset to first page when fetching new data
    setSelectedCategory("All"); // Reset filter when fetching new data
    setSortBy("name"); // Reset sort when fetching new data
    try {
      const res = await axios.post("/generate_events", {
        query: "Things to do in Valdosta GA",
      });
      console.log("Backend response:", res.data);
      setEvents(res.data.events || []);
      setAttractions(res.data.attractions || []);
    } catch (err) {
      console.error("Error fetching events:", err);
      alert("Failed to fetch events. Check console for details.");
    }
    setLoading(false);
  };

  // Auto-fetch data when component mounts
  useEffect(() => {
    fetchEvents();
  }, []);

  // Get unique categories from all attractions
  const allCategories = [
    "All",
    ...new Set(
      attractions.flatMap((attraction) => attraction.categories || [])
    ),
  ];

  // Filter and sort attractions
  const filteredAndSortedAttractions = attractions
    .filter((attraction) => {
      if (selectedCategory === "All") return true;
      return (
        attraction.categories &&
        attraction.categories.includes(selectedCategory)
      );
    })
    .sort((a, b) => {
      switch (sortBy) {
        case "name":
          return a.title.localeCompare(b.title);
        case "category":
          const aCategory =
            a.categories && a.categories[0] ? a.categories[0] : "";
          const bCategory =
            b.categories && b.categories[0] ? b.categories[0] : "";
          return aCategory.localeCompare(bCategory);
        default:
          return 0;
      }
    });

  // Pagination logic
  const totalPages = Math.ceil(
    filteredAndSortedAttractions.length / attractionsPerPage
  );
  const startIndex = (currentPage - 1) * attractionsPerPage;
  const endIndex = startIndex + attractionsPerPage;
  const currentAttractions = filteredAndSortedAttractions.slice(
    startIndex,
    endIndex
  );

  return (
    <div style={{ maxWidth: "900px", margin: "40px auto 0 auto" }}>
      {/* Hero Section with Background */}
      <div
        style={{
          backgroundImage:
            "url('https://www.valdostacity.com/sites/default/files/uploads/dji_0723-hdr-pano.jpg')",
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
          position: "relative",
          padding: "80px 40px",
          borderRadius: "12px",
          marginBottom: "40px",
          boxShadow: "0 8px 32px rgba(0,0,0,0.1)",
          overflow: "hidden",
        }}
      >
        {/* Overlay for better text readability */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.4)",
            zIndex: 1,
          }}
        />

        {/* Content */}
        <div style={{ position: "relative", zIndex: 2, textAlign: "center" }}>
          <h1
            style={{
              color: "white",
              fontSize: "2.5rem",
              fontWeight: "700",
              margin: "0 0 20px 0",
              textShadow: "2px 2px 4px rgba(0,0,0,0.7)",
              lineHeight: "1.2",
            }}
          >
            🌟 Wonder what to do in Valdosta GA? 🌟
          </h1>

          <p
            style={{
              color: "rgba(255,255,255,0.9)",
              fontSize: "1.2rem",
              textShadow: "1px 1px 2px rgba(0,0,0,0.7)",
              maxWidth: "600px",
              margin: "0 auto 30px auto",
            }}
          >
            Discover amazing events and attractions in the heart of South
            Georgia
          </p>

          <button
            onClick={fetchEvents}
            disabled={loading}
            style={{
              padding: "16px 32px",
              fontSize: "18px",
              fontWeight: "600",
              backgroundColor: loading ? "#95a5a6" : "#e74c3c",
              color: "white",
              border: "none",
              borderRadius: "50px",
              cursor: loading ? "not-allowed" : "pointer",
              boxShadow: "0 4px 15px rgba(231, 76, 60, 0.3)",
              transition: "all 0.3s ease",
              textTransform: "uppercase",
              letterSpacing: "1px",
              transform: loading ? "none" : "translateY(0)",
            }}
            onMouseEnter={(e) => {
              if (!loading) {
                e.target.style.transform = "translateY(-2px)";
                e.target.style.boxShadow = "0 6px 20px rgba(231, 76, 60, 0.4)";
                e.target.style.backgroundColor = "#c0392b";
              }
            }}
            onMouseLeave={(e) => {
              if (!loading) {
                e.target.style.transform = "translateY(0)";
                e.target.style.boxShadow = "0 4px 15px rgba(231, 76, 60, 0.3)";
                e.target.style.backgroundColor = "#e74c3c";
              }
            }}
          >
            {loading ? "🔄 Loading..." : "🔄 Refresh Data"}
          </button>
        </div>
      </div>

      {loading && (
        <div
          style={{
            textAlign: "center",
            padding: "20px",
            backgroundColor: "#f8f9fa",
            borderRadius: "8px",
            marginBottom: "20px",
            border: "1px solid #e9ecef",
          }}
        >
          <p
            style={{
              margin: 0,
              fontSize: "16px",
              color: "#495057",
              fontWeight: "500",
            }}
          >
            🔄 Discovering amazing events and attractions in Valdosta...
          </p>
        </div>
      )}

      {/* Tab Navigation */}
      {(events.length > 0 || attractions.length > 0) && (
        <div
          style={{
            display: "flex",
            borderBottom: "2px solid #e9ecef",
            marginBottom: "30px",
            backgroundColor: "#f8f9fa",
            borderRadius: "8px 8px 0 0",
            overflow: "hidden",
          }}
        >
          <button
            onClick={() => setActiveTab("events")}
            style={{
              flex: 1,
              padding: "15px 20px",
              border: "none",
              backgroundColor:
                activeTab === "events" ? "#3498db" : "transparent",
              color: activeTab === "events" ? "white" : "#495057",
              fontSize: "16px",
              fontWeight: "600",
              cursor: "pointer",
              transition: "all 0.3s ease",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
            }}
            onMouseEnter={(e) => {
              if (activeTab !== "events") {
                e.target.style.backgroundColor = "#e9ecef";
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== "events") {
                e.target.style.backgroundColor = "transparent";
              }
            }}
          >
            📅 Scheduled Events
            {events.length > 0 && (
              <span
                style={{
                  backgroundColor:
                    activeTab === "events"
                      ? "rgba(255,255,255,0.3)"
                      : "#3498db",
                  color: activeTab === "events" ? "white" : "white",
                  padding: "2px 8px",
                  borderRadius: "12px",
                  fontSize: "12px",
                  fontWeight: "500",
                }}
              >
                {events.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("attractions")}
            style={{
              flex: 1,
              padding: "15px 20px",
              border: "none",
              backgroundColor:
                activeTab === "attractions" ? "#3498db" : "transparent",
              color: activeTab === "attractions" ? "white" : "#495057",
              fontSize: "16px",
              fontWeight: "600",
              cursor: "pointer",
              transition: "all 0.3s ease",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
            }}
            onMouseEnter={(e) => {
              if (activeTab !== "attractions") {
                e.target.style.backgroundColor = "#e9ecef";
              }
            }}
            onMouseLeave={(e) => {
              if (activeTab !== "attractions") {
                e.target.style.backgroundColor = "transparent";
              }
            }}
          >
            🏛️ Places to Visit
            {attractions.length > 0 && (
              <span
                style={{
                  backgroundColor:
                    activeTab === "attractions"
                      ? "rgba(255,255,255,0.3)"
                      : "#3498db",
                  color: activeTab === "attractions" ? "white" : "white",
                  padding: "2px 8px",
                  borderRadius: "12px",
                  fontSize: "12px",
                  fontWeight: "500",
                }}
              >
                {attractions.length}
              </span>
            )}
          </button>
        </div>
      )}

      {/* Events Tab Content */}
      {activeTab === "events" && events.length > 0 && (
        <div>
          <h2
            style={{
              color: "#2c3e50",
              borderBottom: "2px solid #3498db",
              paddingBottom: "10px",
              marginBottom: "20px",
            }}
          >
            📅 Scheduled Events
          </h2>
          <FullCalendar
            plugins={[dayGridPlugin, interactionPlugin]}
            initialView="dayGridMonth"
            events={events}
            eventClick={(info) => {
              if (info.event.url) {
                window.open(info.event.url, "_blank"); // Open event in new tab
                info.jsEvent.preventDefault(); // Prevent default navigation
              }
            }}
            eventDidMount={(info) => {
              const desc =
                info.event.extendedProps.description || "No description";
              const url = info.event.extendedProps.url
                ? `<a href="${info.event.extendedProps.url}" target="_blank" rel="noopener noreferrer">More info</a>`
                : "";
              tippy(info.el, {
                content: `<strong>${info.event.title}</strong><br>${desc}<br>${url}`,
                allowHTML: true,
              });
            }}
          />
        </div>
      )}

      {/* Attractions Tab Content */}
      {activeTab === "attractions" && attractions.length > 0 && (
        <div>
          <h2
            style={{
              color: "#2c3e50",
              borderBottom: "2px solid #3498db",
              paddingBottom: "10px",
              marginBottom: "20px",
            }}
          >
            🏛️ Places to Visit in Valdosta
          </h2>

          {/* Filter and Sort Controls */}
          <div
            style={{
              display: "flex",
              gap: "20px",
              marginBottom: "20px",
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <label style={{ fontWeight: "500", color: "#2c3e50" }}>
                Filter by Category:
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => {
                  setSelectedCategory(e.target.value);
                  setCurrentPage(1); // Reset to first page when filtering
                }}
                style={{
                  padding: "6px 12px",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                  fontSize: "14px",
                  backgroundColor: "white",
                }}
              >
                {allCategories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <label style={{ fontWeight: "500", color: "#2c3e50" }}>
                Sort by:
              </label>
              <select
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  setCurrentPage(1); // Reset to first page when sorting
                }}
                style={{
                  padding: "6px 12px",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                  fontSize: "14px",
                  backgroundColor: "white",
                }}
              >
                <option value="name">Name (A-Z)</option>
                <option value="category">Category</option>
              </select>
            </div>

            <div
              style={{
                fontSize: "14px",
                color: "#666",
                marginLeft: "auto",
              }}
            >
              Showing {filteredAndSortedAttractions.length} attraction
              {filteredAndSortedAttractions.length !== 1 ? "s" : ""}
            </div>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: "20px",
              marginTop: "20px",
            }}
          >
            {currentAttractions.map((attraction, index) => (
              <div
                key={index}
                style={{
                  border: "1px solid #e0e0e0",
                  borderRadius: "8px",
                  padding: "20px",
                  backgroundColor: "#f9f9f9",
                  boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                  transition: "transform 0.2s ease, box-shadow 0.2s ease",
                  cursor: "pointer",
                }}
                onMouseEnter={(e) => {
                  e.target.style.transform = "translateY(-2px)";
                  e.target.style.boxShadow = "0 4px 8px rgba(0,0,0,0.15)";
                }}
                onMouseLeave={(e) => {
                  e.target.style.transform = "translateY(0)";
                  e.target.style.boxShadow = "0 2px 4px rgba(0,0,0,0.1)";
                }}
                onClick={() => {
                  if (attraction.url) {
                    window.open(
                      attraction.url,
                      "_blank",
                      "noopener,noreferrer"
                    );
                  }
                }}
              >
                <h3
                  style={{
                    margin: "0 0 10px 0",
                    color: "#2c3e50",
                    fontSize: "18px",
                    fontWeight: "600",
                  }}
                >
                  {attraction.title.replace("Visit: ", "")}
                </h3>

                {/* Categories */}
                {attraction.categories && attraction.categories.length > 0 && (
                  <div style={{ marginBottom: "10px" }}>
                    {attraction.categories.map((category, catIndex) => (
                      <span
                        key={catIndex}
                        style={{
                          display: "inline-block",
                          backgroundColor: "#e8f4fd",
                          color: "#2c3e50",
                          padding: "2px 8px",
                          borderRadius: "12px",
                          fontSize: "12px",
                          margin: "2px 4px 2px 0",
                          fontWeight: "500",
                        }}
                      >
                        {category}
                      </span>
                    ))}
                  </div>
                )}

                {attraction.description && (
                  <p
                    style={{
                      margin: "0 0 15px 0",
                      color: "#666",
                      lineHeight: "1.5",
                      fontSize: "14px",
                    }}
                  >
                    {attraction.description}
                  </p>
                )}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    color: "#3498db",
                    fontSize: "14px",
                    fontWeight: "500",
                  }}
                >
                  <span style={{ marginRight: "5px" }}>🔗</span>
                  {(() => {
                    // Determine source based on categories or URL
                    const categories = attraction.categories || [];
                    const url = attraction.url || "";

                    if (
                      categories.includes("Explore Georgia") ||
                      url.includes("exploregeorgia.org")
                    ) {
                      return "Learn more on Explore Georgia";
                    } else if (
                      categories.includes("TripAdvisor") ||
                      url.includes("tripadvisor.com")
                    ) {
                      return "Learn more on TripAdvisor";
                    } else if (
                      categories.includes("Wanderlog") ||
                      url.includes("wanderlog.com")
                    ) {
                      return "Learn more on Wanderlog";
                    } else {
                      return "Learn more";
                    }
                  })()}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                marginTop: "30px",
                gap: "10px",
              }}
            >
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                style={{
                  padding: "8px 16px",
                  border: "1px solid #3498db",
                  borderRadius: "4px",
                  backgroundColor: currentPage === 1 ? "#f5f5f5" : "white",
                  color: currentPage === 1 ? "#999" : "#3498db",
                  cursor: currentPage === 1 ? "not-allowed" : "pointer",
                  fontSize: "14px",
                }}
              >
                Previous
              </button>

              <span
                style={{
                  padding: "8px 16px",
                  color: "#2c3e50",
                  fontSize: "14px",
                  fontWeight: "500",
                }}
              >
                Page {currentPage} of {totalPages}
              </span>

              <button
                onClick={() =>
                  setCurrentPage(Math.min(totalPages, currentPage + 1))
                }
                disabled={currentPage === totalPages}
                style={{
                  padding: "8px 16px",
                  border: "1px solid #3498db",
                  borderRadius: "4px",
                  backgroundColor:
                    currentPage === totalPages ? "#f5f5f5" : "white",
                  color: currentPage === totalPages ? "#999" : "#3498db",
                  cursor:
                    currentPage === totalPages ? "not-allowed" : "pointer",
                  fontSize: "14px",
                }}
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {/* No Content Message */}
      {activeTab === "events" && events.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            backgroundColor: "#f8f9fa",
            borderRadius: "8px",
            border: "1px solid #e9ecef",
          }}
        >
          <h3 style={{ color: "#6c757d", margin: "0 0 10px 0" }}>
            📅 No Scheduled Events Found
          </h3>
          <p style={{ color: "#6c757d", margin: 0 }}>
            No events are currently scheduled. Try refreshing or check back
            later!
          </p>
        </div>
      )}

      {activeTab === "attractions" && attractions.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            backgroundColor: "#f8f9fa",
            borderRadius: "8px",
            border: "1px solid #e9ecef",
          }}
        >
          <h3 style={{ color: "#6c757d", margin: "0 0 10px 0" }}>
            🏛️ No Attractions Found
          </h3>
          <p style={{ color: "#6c757d", margin: 0 }}>
            No attractions are currently available. Try refreshing or check back
            later!
          </p>
        </div>
      )}

      {/* Simple Footer */}
      <footer
        style={{
          marginTop: "60px",
          marginBottom: "40px",
          textAlign: "center",
          padding: "20px",
          borderTop: "1px solid #e9ecef",
        }}
      >
        <p
          style={{
            margin: "0",
            color: "#6c757d",
            fontSize: "14px",
            lineHeight: "1.5",
          }}
        >
          Made with ❤️ for Valdosta, Georgia | Discover amazing events and
          attractions in the heart of South Georgia
        </p>
      </footer>
    </div>
  );
}

export default App;
