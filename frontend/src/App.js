// frontend/App.js
import React, { useState, useEffect } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import tippy from "tippy.js";
import "tippy.js/dist/tippy.css";
import Settings from "./Settings";

function App() {
  const [events, setEvents] = useState([]);
  const [classes, setClasses] = useState([]);
  const [meetings, setMeetings] = useState([]);
  const [attractions, setAttractions] = useState([]);
  const [loading, setLoading] = useState({
    events: false,
    classes: false,
    meetings: false,
    attractions: false,
  });
  const [progress, setProgress] = useState({
    events: { current: 0, total: 0, source: "" },
    classes: { current: 0, total: 0, source: "" },
    meetings: { current: 0, total: 0, source: "" },
    attractions: { current: 0, total: 0, source: "" },
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [sortBy, setSortBy] = useState("name");
  const [activeTab, setActiveTab] = useState("events");
  const [showSettings, setShowSettings] = useState(false);
  const attractionsPerPage = 6;

  // Use ref to store EventSource so we can clean it up
  const eventSourceRefs = React.useRef({
    events: null,
    classes: null,
    meetings: null,
    attractions: null,
  });

  const fetchCategory = (category) => {
    // Close any existing EventSource connection for this category
    if (eventSourceRefs.current[category]) {
      console.log(`Closing existing EventSource for ${category}`);
      eventSourceRefs.current[category].close();
      eventSourceRefs.current[category] = null;
    }

    setLoading((prev) => ({ ...prev, [category]: true }));
    setProgress((prev) => ({
      ...prev,
      [category]: { current: 0, total: 0, source: "" },
    }));

    // Clear previous data for this category
    if (category === "events") setEvents([]);
    if (category === "classes") setClasses([]);
    if (category === "meetings") setMeetings([]);
    if (category === "attractions") {
      setAttractions([]);
      setCurrentPage(1);
      setSelectedCategory("All");
      setSortBy("name");
    }

    try {
      // Use Server-Sent Events for progressive loading
      const eventSource = new EventSource(
        `/generate_events_stream?category=${category}`
      );
      eventSourceRefs.current[category] = eventSource;

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const timestamp = new Date().toLocaleTimeString();
        console.log(`[${timestamp}] SSE message for ${category}:`, data.type, data);

        if (data.type === "init") {
          // Initialize progress
          console.log(
            `[${timestamp}] ✅ Initialized ${category} with ${data.total} sources`
          );
          setProgress((prev) => ({
            ...prev,
            [category]: {
              current: 0,
              total: data.total,
              source: "Initializing...",
            },
          }));
        } else if (data.type === category && (data.type === "events" || data.type === "classes" || data.type === "meetings")) {
          // Add calendar items ONLY if data.type matches the requested category
          // This prevents cross-contamination between categories
          console.log(
            `[${timestamp}] 📅 Adding ${data.events?.length || 0} ${category} from "${data.source}" (${data.current}/${data.total})`
          );
          const items = data.events || [];

          if (category === "events") {
            setEvents((prev) => [...prev, ...items]);
          } else if (category === "classes") {
            setClasses((prev) => [...prev, ...items]);
          } else if (category === "meetings") {
            setMeetings((prev) => [...prev, ...items]);
          }
        } else if ((data.type === "events" || data.type === "classes" || data.type === "meetings") && data.type !== category) {
          // Category mismatch - log warning but don't add data
          console.warn(
            `[${timestamp}] ⚠️  Category mismatch: Expected ${category} but received ${data.type}. Ignoring data.`
          );

          setProgress((prev) => ({
            ...prev,
            [category]: {
              current: data.current,
              total: data.total,
              source: data.source,
            },
          }));
        } else if (data.type === "attractions") {
          // Add attractions progressively
          console.log(
            `[${timestamp}] 🏛️ Adding ${data.attractions.length} attractions from "${data.source}" (${data.current}/${data.total})`
          );
          setAttractions((prev) => {
            const newAttractions = [...prev, ...data.attractions];
            console.log(
              `[${timestamp}] 📊 Total attractions now: ${newAttractions.length}`
            );
            return newAttractions;
          });
          setProgress((prev) => ({
            ...prev,
            [category]: {
              current: data.current,
              total: data.total,
              source: data.source,
            },
          }));
        } else if (data.type === "progress") {
          // Handle progress messages
          console.log(`[${timestamp}] 📊 Progress for ${category}: ${data.message}`);
          setProgress((prev) => ({
            ...prev,
            [category]: {
              current: data.current,
              total: data.total,
              source: data.source,
            },
          }));
        } else if (data.type === "error") {
          // Handle error but continue
          console.error(
            `[${timestamp}] ❌ Error scraping ${data.source}:`,
            data.error
          );
          setProgress((prev) => ({
            ...prev,
            [category]: {
              current: data.current,
              total: data.total,
              source: data.source,
            },
          }));
        } else if (data.type === "complete") {
          // All done!
          console.log(`[${timestamp}] ✅ All scraping complete for ${category}!`);
          setLoading((prev) => ({ ...prev, [category]: false }));
          if (eventSourceRefs.current[category]) {
            eventSourceRefs.current[category].close();
            eventSourceRefs.current[category] = null;
          }
        }
      };

      eventSource.onerror = (error) => {
        console.error(`SSE error for ${category}:`, error);
        alert(`Failed to fetch ${category}. Check console for details.`);
        setLoading((prev) => ({ ...prev, [category]: false }));
        if (eventSourceRefs.current[category]) {
          eventSourceRefs.current[category].close();
          eventSourceRefs.current[category] = null;
        }
      };
    } catch (err) {
      console.error(`Error setting up event stream for ${category}:`, err);
      alert(`Failed to fetch ${category}. Check console for details.`);
      setLoading((prev) => ({ ...prev, [category]: false }));
    }
  };

  // Cleanup EventSource on unmount (no auto-fetch - user must click Refresh Data)
  useEffect(() => {
    // Cleanup function to close EventSource when component unmounts
    return () => {
      Object.keys(eventSourceRefs.current).forEach((category) => {
        if (eventSourceRefs.current[category]) {
          console.log(`Cleaning up EventSource for ${category} on unmount`);
          eventSourceRefs.current[category].close();
          eventSourceRefs.current[category] = null;
        }
      });
    };
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

  // Show settings page if requested
  if (showSettings) {
    return <Settings onBack={() => setShowSettings(false)} />;
  }

  // Render calendar for a given category
  const renderCalendar = (categoryData, categoryName) => {
    const prog = progress[categoryName];
    const isLoading = loading[categoryName];
    const anyLoading = loading.events || loading.classes || loading.meetings || loading.attractions;

    return (
      <div>
        <h2
          style={{
            color: "#2c3e50",
            borderBottom: "2px solid #3498db",
            paddingBottom: "10px",
            marginBottom: "20px",
          }}
        >
          📅 {categoryName.charAt(0).toUpperCase() + categoryName.slice(1)} ({categoryData.length} total)
        </h2>

        {/* Refresh Button */}
        <div style={{ marginBottom: "20px" }}>
          <button
            onClick={() => fetchCategory(categoryName)}
            disabled={anyLoading}
            style={{
              padding: "12px 24px",
              fontSize: "16px",
              fontWeight: "600",
              backgroundColor: anyLoading ? "#95a5a6" : "#e74c3c",
              color: "white",
              border: "none",
              borderRadius: "8px",
              cursor: anyLoading ? "not-allowed" : "pointer",
              boxShadow: "0 4px 12px rgba(231, 76, 60, 0.3)",
              transition: "all 0.3s ease",
            }}
            onMouseEnter={(e) => {
              if (!anyLoading) {
                e.target.style.backgroundColor = "#c0392b";
                e.target.style.transform = "translateY(-2px)";
              }
            }}
            onMouseLeave={(e) => {
              if (!anyLoading) {
                e.target.style.backgroundColor = "#e74c3c";
                e.target.style.transform = "translateY(0)";
              }
            }}
          >
            {isLoading ? "🔄 Loading..." : "🔄 Refresh Data"}
          </button>
        </div>

        {/* Progress Bar */}
        {isLoading && (
          <div
            style={{
              padding: "20px",
              backgroundColor: "#f8f9fa",
              borderRadius: "8px",
              marginBottom: "20px",
              border: "2px solid #3498db",
            }}
          >
            <div style={{ marginBottom: "12px" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "8px",
                }}
              >
                <p
                  style={{
                    margin: 0,
                    fontSize: "15px",
                    color: "#2c3e50",
                    fontWeight: "600",
                  }}
                >
                  🔄 Loading {categoryName}...
                </p>
                {prog.total > 0 && (
                  <span
                    style={{
                      fontSize: "14px",
                      color: "#3498db",
                      fontWeight: "600",
                    }}
                  >
                    {prog.current} / {prog.total}
                  </span>
                )}
              </div>
              {prog.source && (
                <p
                  style={{
                    margin: "0 0 10px 0",
                    fontSize: "13px",
                    color: "#666",
                  }}
                >
                  Scraping: <strong>{prog.source}</strong>
                </p>
              )}
              {prog.total === 0 && (
                <p
                  style={{
                    margin: "0 0 10px 0",
                    fontSize: "13px",
                    color: "#666",
                  }}
                >
                  Connecting to server...
                </p>
              )}
            </div>

            {/* Progress Bar */}
            <div
              style={{
                width: "100%",
                height: "10px",
                backgroundColor: "#e9ecef",
                borderRadius: "5px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width:
                    prog.total > 0 ? `${(prog.current / prog.total) * 100}%` : "100%",
                  height: "100%",
                  backgroundColor: "#3498db",
                  borderRadius: "5px",
                  transition: "width 0.3s ease",
                  backgroundImage:
                    "linear-gradient(45deg, rgba(255,255,255,0.2) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.2) 50%, rgba(255,255,255,0.2) 75%, transparent 75%, transparent)",
                  backgroundSize: "40px 40px",
                  animation: "progress-bar-stripes 1s linear infinite",
                }}
              />
            </div>
          </div>
        )}

        {/* Calendar */}
        {categoryData.length > 0 && (
          <FullCalendar
            plugins={[dayGridPlugin, interactionPlugin]}
            initialView="dayGridMonth"
            events={categoryData}
            eventClick={(info) => {
              if (info.event.url) {
                window.open(info.event.url, "_blank");
                info.jsEvent.preventDefault();
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
        )}

        {/* No Content Message */}
        {!isLoading && categoryData.length === 0 && (
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
              📅 No {categoryName} Found
            </h3>
            <p style={{ color: "#6c757d", margin: 0 }}>
              No {categoryName} are currently available. Click "Refresh Data" to load them.
            </p>
          </div>
        )}

        <style>
          {`
            @keyframes progress-bar-stripes {
              0% { background-position: 40px 0; }
              100% { background-position: 0 0; }
            }
          `}
        </style>
      </div>
    );
  };

  // Otherwise show main calendar
  return (
    <div style={{ maxWidth: "900px", margin: "40px auto 0 auto", position: "relative" }}>
      {/* Settings Button - Floating */}
      <button
        onClick={() => setShowSettings(true)}
        style={{
          position: "fixed",
          top: "20px",
          right: "20px",
          padding: "12px 20px",
          backgroundColor: "#34495e",
          color: "white",
          border: "none",
          borderRadius: "50px",
          cursor: "pointer",
          fontSize: "14px",
          fontWeight: "600",
          boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
          zIndex: 1000,
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
        onMouseEnter={(e) => {
          e.target.style.backgroundColor = "#2c3e50";
          e.target.style.transform = "scale(1.05)";
        }}
        onMouseLeave={(e) => {
          e.target.style.backgroundColor = "#34495e";
          e.target.style.transform = "scale(1)";
        }}
      >
        ⚙️ Settings
      </button>

      {/* Hero Section with Background */}
      <div
        style={{
          backgroundImage:
            "url('https://www.valdostacity.com/sites/default/files/uploads/dji_0723-hdr-pano.jpg')",
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
          position: "relative",
          padding: "60px 40px",
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
              margin: "0 0 15px 0",
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
              margin: "0 auto",
            }}
          >
            Discover amazing events, classes, meetings, and places to visit in the heart of South
            Georgia
          </p>
        </div>
      </div>

      {/* Tab Navigation */}
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
          📅 Events
          {events.length > 0 && (
            <span
              style={{
                backgroundColor:
                  activeTab === "events"
                    ? "rgba(255,255,255,0.3)"
                    : "#3498db",
                color: "white",
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
          onClick={() => setActiveTab("classes")}
          style={{
            flex: 1,
            padding: "15px 20px",
            border: "none",
            backgroundColor:
              activeTab === "classes" ? "#3498db" : "transparent",
            color: activeTab === "classes" ? "white" : "#495057",
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
            if (activeTab !== "classes") {
              e.target.style.backgroundColor = "#e9ecef";
            }
          }}
          onMouseLeave={(e) => {
            if (activeTab !== "classes") {
              e.target.style.backgroundColor = "transparent";
            }
          }}
        >
          📚 Classes
          {classes.length > 0 && (
            <span
              style={{
                backgroundColor:
                  activeTab === "classes"
                    ? "rgba(255,255,255,0.3)"
                    : "#3498db",
                color: "white",
                padding: "2px 8px",
                borderRadius: "12px",
                fontSize: "12px",
                fontWeight: "500",
              }}
            >
              {classes.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("meetings")}
          style={{
            flex: 1,
            padding: "15px 20px",
            border: "none",
            backgroundColor:
              activeTab === "meetings" ? "#3498db" : "transparent",
            color: activeTab === "meetings" ? "white" : "#495057",
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
            if (activeTab !== "meetings") {
              e.target.style.backgroundColor = "#e9ecef";
            }
          }}
          onMouseLeave={(e) => {
            if (activeTab !== "meetings") {
              e.target.style.backgroundColor = "transparent";
            }
          }}
        >
          🤝 Meetings
          {meetings.length > 0 && (
            <span
              style={{
                backgroundColor:
                  activeTab === "meetings"
                    ? "rgba(255,255,255,0.3)"
                    : "#3498db",
                color: "white",
                padding: "2px 8px",
                borderRadius: "12px",
                fontSize: "12px",
                fontWeight: "500",
              }}
            >
              {meetings.length}
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
          🏛️ Visit Valdosta
          {attractions.length > 0 && (
            <span
              style={{
                backgroundColor:
                  activeTab === "attractions"
                    ? "rgba(255,255,255,0.3)"
                    : "#3498db",
                color: "white",
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

      {/* Tab Content */}
      {activeTab === "events" && renderCalendar(events, "events")}
      {activeTab === "classes" && (
        <>
          {renderCalendar(classes, "classes")}
          <div
            style={{
              margin: "20px",
              padding: "15px",
              backgroundColor: "#f8f9fa",
              borderLeft: "4px solid #3498db",
              borderRadius: "4px",
              fontSize: "14px",
              color: "#495057",
            }}
          >
            <strong>Note:</strong> This calendar shows a subset of available classes
            with confirmed dates. For a complete list of all classes and workshops,
            please visit the{" "}
            <a
              href="https://turnercenter.org/classes"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: "#3498db",
                textDecoration: "none",
                fontWeight: "600",
              }}
            >
              Turner Center for the Arts website
            </a>
            .
          </div>
        </>
      )}
      {activeTab === "meetings" && renderCalendar(meetings, "meetings")}

      {/* Visit Valdosta Tab Content */}
      {activeTab === "attractions" && (
        <div
          style={{
            maxWidth: "900px",
            margin: "0 auto",
            padding: "40px 20px",
          }}
        >
          <div
            style={{
              textAlign: "center",
              padding: "40px 30px",
              backgroundColor: "#fff8e1",
              borderRadius: "12px",
              border: "2px solid #ffd54f",
            }}
          >
            <h2
              style={{
                color: "#2c3e50",
                margin: "0 0 15px 0",
                fontSize: "28px",
                fontWeight: "600",
              }}
            >
              🏨 Plan Your Stay in Valdosta
            </h2>
            <p
              style={{
                color: "#495057",
                fontSize: "18px",
                lineHeight: "1.7",
                margin: "0 0 25px 0",
              }}
            >
              Your ultimate destination with entertainment for everyone and adventure around every corner!
              Whether you're visiting for a weekend getaway or an extended stay,
              Valdosta offers comfortable accommodations, warm Southern hospitality,
              and endless opportunities to create lasting memories.
            </p>
            <a
              href="https://visitvaldosta.org/"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-block",
                padding: "14px 36px",
                fontSize: "18px",
                fontWeight: "600",
                backgroundColor: "#ffd54f",
                color: "#2c3e50",
                textDecoration: "none",
                borderRadius: "8px",
                transition: "all 0.3s ease",
                border: "2px solid #ffc107",
              }}
              onMouseEnter={(e) => {
                e.target.style.backgroundColor = "#ffc107";
                e.target.style.transform = "translateY(-2px)";
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = "#ffd54f";
                e.target.style.transform = "translateY(0)";
              }}
            >
              Visit Valdosta Website →
            </a>
          </div>
        </div>
      )}

      {/* Remove all the old attractions content below */}
      {activeTab === "attractions-old" && (
        <div>
          <h2
            style={{
              color: "#2c3e50",
              borderBottom: "2px solid #3498db",
              paddingBottom: "10px",
              marginBottom: "20px",
            }}
          >
            🏛️ Places to Visit in Valdosta (OLD)
          </h2>

          {/* Refresh Button */}
          <div style={{ marginBottom: "20px" }}>
            {(() => {
              const anyLoading = loading.events || loading.classes || loading.meetings || loading.attractions;
              return (
                <button
                  onClick={() => fetchCategory("attractions")}
                  disabled={anyLoading}
                  style={{
                    padding: "12px 24px",
                    fontSize: "16px",
                    fontWeight: "600",
                    backgroundColor: anyLoading ? "#95a5a6" : "#e74c3c",
                    color: "white",
                    border: "none",
                    borderRadius: "8px",
                    cursor: anyLoading ? "not-allowed" : "pointer",
                    boxShadow: "0 4px 12px rgba(231, 76, 60, 0.3)",
                    transition: "all 0.3s ease",
                  }}
                  onMouseEnter={(e) => {
                    if (!anyLoading) {
                      e.target.style.backgroundColor = "#c0392b";
                      e.target.style.transform = "translateY(-2px)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!anyLoading) {
                      e.target.style.backgroundColor = "#e74c3c";
                      e.target.style.transform = "translateY(0)";
                    }
                  }}
                >
                  {loading.attractions ? "🔄 Loading..." : "🔄 Refresh Data"}
                </button>
              );
            })()}
          </div>

          {/* Progress Bar */}
          {loading.attractions && (
            <div
              style={{
                padding: "20px",
                backgroundColor: "#f8f9fa",
                borderRadius: "8px",
                marginBottom: "20px",
                border: "2px solid #3498db",
              }}
            >
              <div style={{ marginBottom: "12px" }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "8px",
                  }}
                >
                  <p
                    style={{
                      margin: 0,
                      fontSize: "15px",
                      color: "#2c3e50",
                      fontWeight: "600",
                    }}
                  >
                    🔄 Loading attractions...
                  </p>
                  {progress.attractions.total > 0 && (
                    <span
                      style={{
                        fontSize: "14px",
                        color: "#3498db",
                        fontWeight: "600",
                      }}
                    >
                      {progress.attractions.current} / {progress.attractions.total}
                    </span>
                  )}
                </div>
                {progress.attractions.source && (
                  <p
                    style={{
                      margin: "0 0 10px 0",
                      fontSize: "13px",
                      color: "#666",
                    }}
                  >
                    Scraping: <strong>{progress.attractions.source}</strong>
                  </p>
                )}
              </div>

              <div
                style={{
                  width: "100%",
                  height: "10px",
                  backgroundColor: "#e9ecef",
                  borderRadius: "5px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width:
                      progress.attractions.total > 0
                        ? `${(progress.attractions.current / progress.attractions.total) * 100}%`
                        : "100%",
                    height: "100%",
                    backgroundColor: "#3498db",
                    borderRadius: "5px",
                    transition: "width 0.3s ease",
                    backgroundImage:
                      "linear-gradient(45deg, rgba(255,255,255,0.2) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.2) 50%, rgba(255,255,255,0.2) 75%, transparent 75%, transparent)",
                    backgroundSize: "40px 40px",
                    animation: "progress-bar-stripes 1s linear infinite",
                  }}
                />
              </div>
            </div>
          )}

          {attractions.length > 0 && (
            <>
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
                      setCurrentPage(1);
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
                      setCurrentPage(1);
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
                      e.currentTarget.style.transform = "translateY(-2px)";
                      e.currentTarget.style.boxShadow = "0 4px 8px rgba(0,0,0,0.15)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = "translateY(0)";
                      e.currentTarget.style.boxShadow = "0 2px 4px rgba(0,0,0,0.1)";
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
                        const url = attraction.url || "";
                        try {
                          const urlObj = new URL(url);
                          const hostname = urlObj.hostname.replace(/^www\./, '');
                          const siteName = hostname.split('.')[0].charAt(0).toUpperCase() +
                                          hostname.split('.')[0].slice(1);
                          return `Learn more on ${siteName}`;
                        } catch (e) {
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
            </>
          )}

          {/* Old attractions code kept for reference but never shown */}
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
          Made with ❤️ for Valdosta, Georgia | Discover amazing events, classes, meetings, and
          attractions in the heart of South Georgia
        </p>
      </footer>
    </div>
  );
}

export default App;
