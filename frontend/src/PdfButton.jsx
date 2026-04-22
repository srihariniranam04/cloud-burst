// frontend/src/PdfButton.jsx
import { useState } from "react";
import "./PdfButton.css";

export default function PdfButton({ cityId, cityName, userRole }) {
  const [open,      setOpen]      = useState(false);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState("");
  const [success,   setSuccess]   = useState("");
  const [reportType, setReportType] = useState("monthly");
  const [startDate,  setStartDate]  = useState("");
  const [endDate,    setEndDate]    = useState("");

  // Viewer cannot generate — only download existing
  const canGenerate =
    userRole?.toLowerCase() === "admin" ||
    userRole?.toLowerCase() === "analyst";

  // ── Auto-fill date range when report type changes ──
  const handleReportTypeChange = (type) => {
    setReportType(type);
    setError("");
    setSuccess("");

    const today = new Date();
    const fmt   = (d) => d.toISOString().split("T")[0];

    if (type === "daily") {
      setStartDate(fmt(today));
      setEndDate(fmt(today));
    } else if (type === "weekly") {
      const weekAgo = new Date(today);
      weekAgo.setDate(today.getDate() - 7);
      setStartDate(fmt(weekAgo));
      setEndDate(fmt(today));
    } else if (type === "monthly") {
      const monthAgo = new Date(today);
      monthAgo.setMonth(today.getMonth() - 1);
      setStartDate(fmt(monthAgo));
      setEndDate(fmt(today));
    } else {
      // custom — let user pick
      setStartDate("");
      setEndDate("");
    }
  };

  // ── Generate report ────────────────────────────────
  const handleGenerate = async () => {
    setError("");
    setSuccess("");

    if (!cityId) {
      setError("Please select a city first.");
      return;
    }
    if (!startDate || !endDate) {
      setError("Please select a date range.");
      return;
    }
    if (startDate > endDate) {
      setError("Start date must be before end date.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/reports/generate", {
        method:      "POST",
        credentials: "include",
        headers:     { "Content-Type": "application/json" },
        body: JSON.stringify({
          city_id:     cityId,
          report_type: reportType,
          start_date:  startDate,
          end_date:    endDate,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        setSuccess(
          `✅ Report generated! ${data.summary?.total_days || 0} days, ` +
          `${data.summary?.total_anomalies || 0} anomalies, ` +
          `${data.summary?.total_cloudbursts || 0} cloudbursts.`
        );
        // Auto-download
        window.open(
          `/api/reports/${data.report_id}/download`,
          "_blank"
        );
      } else {
        setError(data.error || "Report generation failed.");
      }
    } catch (err) {
      setError("Cannot reach server. Make sure Flask is running.");
    } finally {
      setLoading(false);
    }
  };

  if (!canGenerate) {
    return (
      <div className="pdf-viewer-notice">
        <span>📄</span>
        <span>PDF reports are available for download from your Admin or Analyst.</span>
      </div>
    );
  }

  return (
    <div className="pdf-btn-wrapper">
      {/* Trigger button */}
      <button
        className="pdf-trigger-btn"
        onClick={() => { setOpen(!open); setError(""); setSuccess(""); }}
      >
        📄 {open ? "Close" : "Generate PDF Report"}
      </button>

      {/* Expanded panel */}
      {open && (
        <div className="pdf-panel">
          <div className="pdf-panel-title">
            Generate Report — {cityName || "Selected City"}
          </div>

          {/* Report type selector */}
          <div className="pdf-field">
            <label className="pdf-label">Report Type</label>
            <div className="pdf-type-grid">
              {["daily", "weekly", "monthly", "custom"].map((t) => (
                <button
                  key={t}
                  className={`pdf-type-btn ${reportType === t ? "active" : ""}`}
                  onClick={() => handleReportTypeChange(t)}
                >
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Date range */}
          <div className="pdf-date-row">
            <div className="pdf-field">
              <label className="pdf-label">Start Date</label>
              <input
                type="date"
                className="pdf-date-input"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="pdf-field">
              <label className="pdf-label">End Date</label>
              <input
                type="date"
                className="pdf-date-input"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>

          {/* Error / success */}
          {error   && <div className="pdf-error">⚠️ {error}</div>}
          {success && <div className="pdf-success">{success}</div>}

          {/* Generate button */}
          <button
            className={`pdf-generate-btn ${loading ? "loading" : ""}`}
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading ? (
              <><span className="pdf-spinner" /> Generating…</>
            ) : (
              "⬇️ Generate & Download PDF"
            )}
          </button>
        </div>
      )}
    </div>
  );
}