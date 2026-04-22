// src/AnomalyList.jsx
import { useEffect, useState } from "react";
import "./AnomalyList.css";

const PARAM_ICON = {
  rainfall:    "🌧️",
  temperature: "🌡️",
  humidity:    "💧",
  wind_speed:  "💨",
  pressure:    "📊",
};

export default function AnomalyList() {
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);
  const [filter, setFilter]       = useState("all"); // all | HIGH | LOW | open
  const [page, setPage]           = useState(1);
  const PER_PAGE = 10;

  useEffect(() => { fetchAnomalies(); }, []);

  async function fetchAnomalies() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/anomalies/recent?limit=200", {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setAnomalies(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const filtered = filter === "all"
    ? anomalies
    : filter === "open"
      ? anomalies.filter(a => a.status === "open")
      : anomalies.filter(a => a.deviation_type === filter);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const paginated  = filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  function handleFilter(f) { setFilter(f); setPage(1); }

  const counts = {
    all:  anomalies.length,
    HIGH: anomalies.filter(a => a.deviation_type === "HIGH").length,
    LOW:  anomalies.filter(a => a.deviation_type === "LOW").length,
    open: anomalies.filter(a => a.status === "open").length,
  };

  // Calculate how far observed is from mean (in std devs)
  function deviationScore(row) {
    if (!row.std_dev || row.std_dev == 0) return "—";
    const score = Math.abs((row.observed_value - row.mean_value) / row.std_dev);
    return score.toFixed(1) + "σ";
  }

  return (
    <div className="anomaly-container">
      {/* Header */}
      <div className="anomaly-header">
        <h2>⚠️ Anomaly Detections</h2>
        <button className="refresh-btn" onClick={fetchAnomalies} disabled={loading}>
          {loading ? "Loading…" : "↻ Refresh"}
        </button>
      </div>

      {/* Filter Bar */}
      <div className="anomaly-filters">
        {[
          { key: "all",  label: "All" },
          { key: "HIGH", label: "🔺 High" },
          { key: "LOW",  label: "🔻 Low" },
          { key: "open", label: "🔔 Open" },
        ].map(f => (
          <button
            key={f.key}
            className={`filter-btn ${filter === f.key ? "active" : ""} filter-${f.key.toLowerCase()}`}
            onClick={() => handleFilter(f.key)}
          >
            {f.label}
            <span className="filter-count">{counts[f.key]}</span>
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="anomaly-error">
          ⚠️ Could not load anomalies: {error}
          <button onClick={fetchAnomalies}>Retry</button>
        </div>
      )}

      {/* Skeleton */}
      {loading && (
        <div className="anomaly-skeleton">
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton-row" />)}
        </div>
      )}

      {/* Empty */}
      {!loading && !error && filtered.length === 0 && (
        <div className="anomaly-empty">
          <span>✅</span>
          <p>No anomalies found{filter !== "all" ? ` for filter: ${filter}` : ""}.</p>
          <small>Run the anomaly detection script to populate this table.</small>
        </div>
      )}

      {/* Table */}
      {!loading && !error && filtered.length > 0 && (
        <>
          <div className="anomaly-table-wrapper">
            <table className="anomaly-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>City</th>
                  <th>State</th>
                  <th>Date</th>
                  <th>Parameter</th>
                  <th>Observed</th>
                  <th>Mean</th>
                  <th>Deviation</th>
                  <th>Type</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {paginated.map((a, i) => {
                  const param = (a.parameter || "").toLowerCase();
                  const icon  = PARAM_ICON[param] || "🔔";
                  const isHigh = a.deviation_type === "HIGH";
                  return (
                    <tr key={a.id || i} className={`row-${a.deviation_type?.toLowerCase()}`}>
                      <td className="row-num">{(page - 1) * PER_PAGE + i + 1}</td>
                      <td className="city-cell">{a.city_name || "—"}</td>
                      <td>{a.state || "—"}</td>
                      <td className="date-cell">{a.detected_date || "—"}</td>
                      <td className="type-cell">{icon} {a.parameter || "—"}</td>
                      <td>{a.observed_value != null ? Number(a.observed_value).toFixed(2) : "—"}</td>
                      <td className="muted">{a.mean_value != null ? Number(a.mean_value).toFixed(2) : "—"}</td>
                      <td className="deviation-cell">{deviationScore(a)}</td>
                      <td>
                        <span className={`anomaly-badge badge-${a.deviation_type?.toLowerCase()}`}>
                          {isHigh ? "▲ HIGH" : "▼ LOW"}
                        </span>
                      </td>
                      <td>
                        <span className={`status-badge status-${a.status}`}>
                          {a.status || "open"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="anomaly-pagination">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
              ‹ Prev
            </button>
            <span>Page {page} of {totalPages} — {filtered.length} records</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
              Next ›
            </button>
          </div>
        </>
      )}
    </div>
  );
}