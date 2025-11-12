// frontend/src/Settings.js
import React, { useState, useEffect } from "react";
import axios from "axios";

function Settings({ onBack }) {
  const [passcode, setPasscode] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [editingSource, setEditingSource] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showPasscodeChange, setShowPasscodeChange] = useState(false);
  const [passcodeChangeData, setPasscodeChangeData] = useState({
    oldPasscode: "",
    newPasscode: "",
    confirmPasscode: "",
  });
  const [passcodeChangeMessage, setPasscodeChangeMessage] = useState("");

  const [formData, setFormData] = useState({
    name: "",
    url: "",
    type: "events",
    enabled: true,
    scraping_method: "auto",
  });

  const handlePasscodeSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await axios.post("/api/verify-passcode", { passcode });
      if (res.data.valid) {
        setIsAuthenticated(true);
        localStorage.setItem("settings_passcode", passcode);
        loadSources(passcode);
      } else {
        setError("Invalid passcode");
      }
    } catch (err) {
      setError("Error verifying passcode");
    }
    setLoading(false);
  };

  const loadSources = async (pass) => {
    try {
      const res = await axios.get("/api/sources", {
        params: { passcode: pass || passcode },
      });
      setSources(res.data.sources || []);
    } catch (err) {
      setError("Error loading sources");
    }
  };

  const isBlockedUrl = (url) => {
    const urlLower = url.toLowerCase();
    const blockedDomains = ['tripadvisor.com', 'tripadvisor.'];
    return blockedDomains.some(domain => urlLower.includes(domain));
  };

  const handleAddSource = async () => {
    if (!formData.name || !formData.url) {
      setError("Name and URL are required");
      return;
    }

    // Check for blocked URLs (frontend validation)
    if (isBlockedUrl(formData.url)) {
      setError("⚠️ This source is not supported due to scraping restrictions. Please use an alternative source.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await axios.post(`/api/sources?passcode=${passcode}`, formData);
      await loadSources();
      setShowAddForm(false);
      resetForm();
    } catch (err) {
      setError(err.response?.data?.detail || "Error adding source");
    }
    setLoading(false);
  };

  const handleUpdateSource = async () => {
    if (!editingSource) return;

    // Check for blocked URLs (frontend validation)
    if (formData.url && isBlockedUrl(formData.url)) {
      setError("⚠️ This source is not supported due to scraping restrictions. Please use an alternative source.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await axios.put(
        `/api/sources/${editingSource.id}?passcode=${passcode}`,
        formData
      );
      await loadSources();
      setShowAddForm(false); // Close the form
      setEditingSource(null);
      resetForm();
    } catch (err) {
      setError(err.response?.data?.detail || "Error updating source");
    }
    setLoading(false);
  };

  const handleDeleteSource = async (sourceId) => {
    if (!window.confirm("Are you sure you want to delete this source?")) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      await axios.delete(`/api/sources/${sourceId}?passcode=${passcode}`);
      await loadSources();
    } catch (err) {
      setError(err.response?.data?.detail || "Error deleting source");
    }
    setLoading(false);
  };

  const startEdit = (source) => {
    setEditingSource(source);
    setFormData({
      name: source.name,
      url: source.url,
      type: source.type,
      enabled: source.enabled,
      scraping_method: source.scraping_method || "auto",
    });
    // Don't show the top form when editing
    setShowAddForm(false);
  };

  const resetForm = () => {
    setFormData({
      name: "",
      url: "",
      type: "events",
      enabled: true,
      scraping_method: "auto",
    });
    setEditingSource(null);
  };

  const handlePasscodeChange = async () => {
    setPasscodeChangeMessage("");
    setError("");

    // Validate inputs
    if (!passcodeChangeData.oldPasscode || !passcodeChangeData.newPasscode || !passcodeChangeData.confirmPasscode) {
      setError("All fields are required");
      return;
    }

    if (passcodeChangeData.newPasscode !== passcodeChangeData.confirmPasscode) {
      setError("New passcode and confirmation do not match");
      return;
    }

    if (passcodeChangeData.newPasscode.length < 6) {
      setError("New passcode must be at least 6 characters");
      return;
    }

    setLoading(true);

    try {
      await axios.post("/api/update-passcode", null, {
        params: {
          old_passcode: passcodeChangeData.oldPasscode,
          new_passcode: passcodeChangeData.newPasscode,
        },
      });

      setPasscodeChangeMessage("Passcode changed successfully! Please use the new passcode next time.");
      setPasscodeChangeData({
        oldPasscode: "",
        newPasscode: "",
        confirmPasscode: "",
      });

      // Update the stored passcode
      setPasscode(passcodeChangeData.newPasscode);
      localStorage.setItem("settings_passcode", passcodeChangeData.newPasscode);

      setTimeout(() => {
        setShowPasscodeChange(false);
        setPasscodeChangeMessage("");
      }, 3000);
    } catch (err) {
      setError(err.response?.data?.detail || "Error changing passcode");
    }
    setLoading(false);
  };

  // Check for saved passcode on mount
  useEffect(() => {
    const savedPasscode = localStorage.getItem("settings_passcode");
    if (savedPasscode) {
      setPasscode(savedPasscode);
      axios.post("/api/verify-passcode", { passcode: savedPasscode }).then((res) => {
        if (res.data.valid) {
          setIsAuthenticated(true);
          // Load sources inline to avoid dependency issues
          axios.get("/api/sources", {
            params: { passcode: savedPasscode },
          }).then((sourcesRes) => {
            setSources(sourcesRes.data.sources || []);
          }).catch((err) => {
            console.error("Error loading sources:", err);
          });
        }
      }).catch((err) => {
        console.error("Error verifying passcode:", err);
      });
    }
  }, []); // Empty dependency array - only run once on mount

  if (!isAuthenticated) {
    return (
      <div
        style={{
          maxWidth: "400px",
          margin: "100px auto",
          padding: "40px",
          backgroundColor: "#f8f9fa",
          borderRadius: "12px",
          boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
        }}
      >
        <h2 style={{ marginBottom: "20px", color: "#2c3e50" }}>
          🔒 Settings Access
        </h2>
        <p style={{ color: "#6c757d", marginBottom: "20px" }}>
          Enter passcode to manage event sources
        </p>
        <form onSubmit={handlePasscodeSubmit}>
          <input
            type="password"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
            placeholder="Enter passcode"
            style={{
              width: "100%",
              padding: "12px",
              border: "1px solid #ddd",
              borderRadius: "6px",
              fontSize: "16px",
              marginBottom: "15px",
            }}
          />
          {error && (
            <p style={{ color: "#e74c3c", marginBottom: "15px" }}>{error}</p>
          )}
          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "12px",
              backgroundColor: "#3498db",
              color: "white",
              border: "none",
              borderRadius: "6px",
              fontSize: "16px",
              fontWeight: "600",
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Verifying..." : "Access Settings"}
          </button>
        </form>
        <button
          onClick={onBack}
          style={{
            width: "100%",
            padding: "12px",
            backgroundColor: "#95a5a6",
            color: "white",
            border: "none",
            borderRadius: "6px",
            fontSize: "14px",
            marginTop: "10px",
            cursor: "pointer",
          }}
        >
          ← Back to Calendar
        </button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "1000px", margin: "40px auto", padding: "0 20px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "30px",
        }}
      >
        <h1 style={{ color: "#2c3e50" }}>⚙️ Event Source Settings</h1>
        <button
          onClick={onBack}
          style={{
            padding: "10px 20px",
            backgroundColor: "#95a5a6",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
          }}
        >
          ← Back to Calendar
        </button>
      </div>

      {error && (
        <div
          style={{
            padding: "15px",
            backgroundColor: "#fee",
            border: "1px solid #fcc",
            borderRadius: "6px",
            marginBottom: "20px",
            color: "#c33",
          }}
        >
          {error}
        </div>
      )}

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "20px",
        }}
      >
        <h2 style={{ color: "#2c3e50" }}>
          📋 Configured Sources ({sources.length})
        </h2>
        <button
          onClick={() => {
            resetForm();
            setShowAddForm(true);
          }}
          style={{
            padding: "10px 20px",
            backgroundColor: "#27ae60",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            fontWeight: "600",
          }}
        >
          + Add New Source
        </button>
      </div>

      {showAddForm && (
        <div
          style={{
            backgroundColor: "#f8f9fa",
            padding: "25px",
            borderRadius: "8px",
            marginBottom: "25px",
            border: "2px solid #3498db",
          }}
        >
          <h3 style={{ marginBottom: "20px", color: "#2c3e50" }}>
            {editingSource ? "Edit Source" : "Add New Source"}
          </h3>
          <div style={{ display: "grid", gap: "15px" }}>
            <div>
              <label style={{ display: "block", marginBottom: "5px", fontWeight: "500" }}>
                Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="e.g., City Events Calendar"
                style={{
                  width: "100%",
                  padding: "10px",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                }}
              />
            </div>
            <div>
              <label style={{ display: "block", marginBottom: "5px", fontWeight: "500" }}>
                URL *
              </label>
              <input
                type="url"
                value={formData.url}
                onChange={(e) =>
                  setFormData({ ...formData, url: e.target.value })
                }
                placeholder="https://example.com/events"
                style={{
                  width: "100%",
                  padding: "10px",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                }}
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}>
              <div>
                <label style={{ display: "block", marginBottom: "5px", fontWeight: "500" }}>
                  Type
                </label>
                <select
                  value={formData.type}
                  onChange={(e) =>
                    setFormData({ ...formData, type: e.target.value })
                  }
                  style={{
                    width: "100%",
                    padding: "10px",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                  }}
                >
                  <option value="events">Events</option>
                  <option value="attractions">Attractions</option>
                </select>
              </div>
              <div>
                <label style={{ display: "block", marginBottom: "5px", fontWeight: "500" }}>
                  Scraping Method
                </label>
                <select
                  value={formData.scraping_method}
                  onChange={(e) =>
                    setFormData({ ...formData, scraping_method: e.target.value })
                  }
                  style={{
                    width: "100%",
                    padding: "10px",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                  }}
                >
                  <option value="auto">Auto-detect</option>
                  <option value="ai">AI-powered</option>
                </select>
              </div>
            </div>
            <div>
              <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <input
                  type="checkbox"
                  checked={formData.enabled}
                  onChange={(e) =>
                    setFormData({ ...formData, enabled: e.target.checked })
                  }
                />
                <span style={{ fontWeight: "500" }}>Enabled</span>
              </label>
            </div>
            <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
              <button
                onClick={editingSource ? handleUpdateSource : handleAddSource}
                disabled={loading}
                style={{
                  padding: "12px 24px",
                  backgroundColor: "#3498db",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: loading ? "not-allowed" : "pointer",
                  fontWeight: "600",
                }}
              >
                {loading ? "Saving..." : editingSource ? "Update" : "Add Source"}
              </button>
              <button
                onClick={() => {
                  setShowAddForm(false);
                  resetForm();
                }}
                style={{
                  padding: "12px 24px",
                  backgroundColor: "#95a5a6",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: "grid", gap: "15px" }}>
        {sources.map((source) => (
          <div
            key={source.id}
            style={{
              backgroundColor: editingSource?.id === source.id ? "#f8f9fa" : (source.enabled ? "white" : "#f8f9fa"),
              padding: "20px",
              borderRadius: "8px",
              border: editingSource?.id === source.id ? "2px solid #f39c12" : `2px solid ${source.enabled ? "#3498db" : "#ddd"}`,
              opacity: source.enabled ? 1 : 0.6,
            }}
          >
            {editingSource?.id === source.id ? (
              // Inline edit form
              <div>
                <h3 style={{ marginBottom: "20px", color: "#2c3e50" }}>
                  ✏️ Editing: {source.name}
                </h3>
                <div style={{ display: "grid", gap: "15px" }}>
                  <div>
                    <label style={{ display: "block", marginBottom: "5px", fontWeight: "500" }}>
                      Name *
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) =>
                        setFormData({ ...formData, name: e.target.value })
                      }
                      placeholder="e.g., City Events Calendar"
                      style={{
                        width: "100%",
                        padding: "10px",
                        border: "1px solid #ddd",
                        borderRadius: "4px",
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", marginBottom: "5px", fontWeight: "500" }}>
                      URL *
                    </label>
                    <input
                      type="url"
                      value={formData.url}
                      onChange={(e) =>
                        setFormData({ ...formData, url: e.target.value })
                      }
                      placeholder="https://example.com/events"
                      style={{
                        width: "100%",
                        padding: "10px",
                        border: "1px solid #ddd",
                        borderRadius: "4px",
                      }}
                    />
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}>
                    <div>
                      <label style={{ display: "block", marginBottom: "5px", fontWeight: "500" }}>
                        Type
                      </label>
                      <select
                        value={formData.type}
                        onChange={(e) =>
                          setFormData({ ...formData, type: e.target.value })
                        }
                        style={{
                          width: "100%",
                          padding: "10px",
                          border: "1px solid #ddd",
                          borderRadius: "4px",
                        }}
                      >
                        <option value="events">Events</option>
                        <option value="attractions">Attractions</option>
                      </select>
                    </div>
                    <div>
                      <label style={{ display: "block", marginBottom: "5px", fontWeight: "500" }}>
                        Scraping Method
                      </label>
                      <select
                        value={formData.scraping_method}
                        onChange={(e) =>
                          setFormData({ ...formData, scraping_method: e.target.value })
                        }
                        style={{
                          width: "100%",
                          padding: "10px",
                          border: "1px solid #ddd",
                          borderRadius: "4px",
                        }}
                      >
                        <option value="auto">Auto-detect</option>
                        <option value="ai">AI-powered</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <input
                        type="checkbox"
                        checked={formData.enabled}
                        onChange={(e) =>
                          setFormData({ ...formData, enabled: e.target.checked })
                        }
                      />
                      <span style={{ fontWeight: "500" }}>Enabled</span>
                    </label>
                  </div>
                  <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                    <button
                      onClick={handleUpdateSource}
                      disabled={loading}
                      style={{
                        padding: "12px 24px",
                        backgroundColor: "#3498db",
                        color: "white",
                        border: "none",
                        borderRadius: "6px",
                        cursor: loading ? "not-allowed" : "pointer",
                        fontWeight: "600",
                      }}
                    >
                      {loading ? "Saving..." : "Save Changes"}
                    </button>
                    <button
                      onClick={() => {
                        setEditingSource(null);
                        resetForm();
                      }}
                      style={{
                        padding: "12px 24px",
                        backgroundColor: "#95a5a6",
                        color: "white",
                        border: "none",
                        borderRadius: "6px",
                        cursor: "pointer",
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              // Normal source display
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "start",
                }}
              >
                <div style={{ flex: 1 }}>
                  <h3 style={{ margin: "0 0 10px 0", color: "#2c3e50" }}>
                    {source.name}
                    {!source.enabled && (
                      <span
                        style={{
                          marginLeft: "10px",
                          fontSize: "12px",
                          backgroundColor: "#95a5a6",
                          color: "white",
                          padding: "2px 8px",
                          borderRadius: "4px",
                        }}
                      >
                        DISABLED
                      </span>
                    )}
                  </h3>
                  <p
                    style={{
                      margin: "0 0 8px 0",
                      color: "#666",
                      fontSize: "14px",
                      wordBreak: "break-all",
                    }}
                  >
                    🔗 {source.url}
                  </p>
                  <div style={{ display: "flex", gap: "10px", fontSize: "13px" }}>
                    <span
                      style={{
                        backgroundColor: source.type === "events" ? "#e8f4fd" : "#fef5e7",
                        padding: "4px 10px",
                        borderRadius: "4px",
                        color: "#2c3e50",
                      }}
                    >
                      {source.type === "events" ? "📅 Events" : "🏛️ Attractions"}
                    </span>
                    <span
                      style={{
                        backgroundColor: "#e8f8f5",
                        padding: "4px 10px",
                        borderRadius: "4px",
                        color: "#2c3e50",
                      }}
                    >
                      {source.scraping_method || "auto"}
                    </span>
                  </div>
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    onClick={() => startEdit(source)}
                    style={{
                      padding: "8px 16px",
                      backgroundColor: "#f39c12",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "14px",
                    }}
                  >
                    ✏️ Edit
                  </button>
                  <button
                    onClick={() => handleDeleteSource(source.id)}
                    style={{
                      padding: "8px 16px",
                      backgroundColor: "#e74c3c",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "14px",
                    }}
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {sources.length === 0 && !showAddForm && (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            backgroundColor: "#f8f9fa",
            borderRadius: "8px",
          }}
        >
          <h3 style={{ color: "#6c757d" }}>No sources configured</h3>
          <p style={{ color: "#6c757d" }}>Click "Add New Source" to get started</p>
        </div>
      )}

      <div
        style={{
          marginTop: "40px",
          padding: "20px",
          backgroundColor: "#e8f4fd",
          borderRadius: "8px",
          border: "1px solid #3498db",
        }}
      >
        <h4 style={{ margin: "0 0 10px 0", color: "#2c3e50" }}>
          🔐 Passcode Management
        </h4>
        <p style={{ margin: 0, color: "#666", fontSize: "14px" }}>
          You can change your passcode for security purposes.
        </p>
        <button
          onClick={() => setShowPasscodeChange(!showPasscodeChange)}
          style={{
            marginTop: "10px",
            padding: "8px 16px",
            backgroundColor: "#3498db",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "14px",
            fontWeight: "600",
          }}
        >
          {showPasscodeChange ? "Cancel" : "Change Passcode"}
        </button>
      </div>

      {showPasscodeChange && (
        <div
          style={{
            marginTop: "20px",
            padding: "25px",
            backgroundColor: "#fff3cd",
            borderRadius: "8px",
            border: "2px solid #ffc107",
          }}
        >
          <h4 style={{ margin: "0 0 15px 0", color: "#2c3e50" }}>
            🔐 Change Passcode
          </h4>
          {passcodeChangeMessage && (
            <div
              style={{
                padding: "12px",
                backgroundColor: "#d4edda",
                border: "1px solid #c3e6cb",
                borderRadius: "6px",
                marginBottom: "15px",
                color: "#155724",
              }}
            >
              {passcodeChangeMessage}
            </div>
          )}
          <div style={{ display: "grid", gap: "15px" }}>
            <div>
              <label style={{ display: "block", marginBottom: "5px", fontWeight: "500" }}>
                Current Passcode *
              </label>
              <input
                type="password"
                value={passcodeChangeData.oldPasscode}
                onChange={(e) =>
                  setPasscodeChangeData({
                    ...passcodeChangeData,
                    oldPasscode: e.target.value,
                  })
                }
                placeholder="Enter current passcode"
                style={{
                  width: "100%",
                  padding: "10px",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                }}
              />
            </div>
            <div>
              <label style={{ display: "block", marginBottom: "5px", fontWeight: "500" }}>
                New Passcode * (min 6 characters)
              </label>
              <input
                type="password"
                value={passcodeChangeData.newPasscode}
                onChange={(e) =>
                  setPasscodeChangeData({
                    ...passcodeChangeData,
                    newPasscode: e.target.value,
                  })
                }
                placeholder="Enter new passcode"
                style={{
                  width: "100%",
                  padding: "10px",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                }}
              />
            </div>
            <div>
              <label style={{ display: "block", marginBottom: "5px", fontWeight: "500" }}>
                Confirm New Passcode *
              </label>
              <input
                type="password"
                value={passcodeChangeData.confirmPasscode}
                onChange={(e) =>
                  setPasscodeChangeData({
                    ...passcodeChangeData,
                    confirmPasscode: e.target.value,
                  })
                }
                placeholder="Confirm new passcode"
                style={{
                  width: "100%",
                  padding: "10px",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                }}
              />
            </div>
            <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
              <button
                onClick={handlePasscodeChange}
                disabled={loading}
                style={{
                  padding: "12px 24px",
                  backgroundColor: "#28a745",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: loading ? "not-allowed" : "pointer",
                  fontWeight: "600",
                }}
              >
                {loading ? "Updating..." : "Update Passcode"}
              </button>
              <button
                onClick={() => {
                  setShowPasscodeChange(false);
                  setPasscodeChangeData({
                    oldPasscode: "",
                    newPasscode: "",
                    confirmPasscode: "",
                  });
                  setPasscodeChangeMessage("");
                  setError("");
                }}
                style={{
                  padding: "12px 24px",
                  backgroundColor: "#95a5a6",
                  color: "white",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Settings;
