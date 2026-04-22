// frontend/src/App.jsx
import { useState, useEffect, useRef, useCallback } from "react";
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import "./App.css";
import Login     from "./Login";
import PdfButton from "./PdfButton";
import AnomalyList from "./AnomalyList";

// ── Region mapping ───────────────────────────────────────
const CITY_REGION = {
  "New Delhi":"North","Jaipur":"North","Chandigarh":"North",
  "Shimla":"North","Dehradun":"North","Srinagar":"North",
  "Lucknow":"North","Leh":"North",
  "Patna":"East","Kolkata":"East","Bhubaneswar":"East",
  "Ranchi":"East","Raipur":"East","Guwahati":"East",
  "Shillong":"East","Aizawl":"East","Kohima":"East",
  "Imphal":"East","Agartala":"East","Itanagar":"East","Gangtok":"East",
  "Mumbai":"West","Ahmedabad":"West","Panaji":"West",
  "Bhopal":"West","Daman":"West","Silvassa":"West",
  "Chennai":"South","Hyderabad":"South","Bengaluru":"South",
  "Thiruvananthapuram":"South","Amaravati":"South",
  "Port Blair":"South","Kavaratti":"South","Puducherry":"South",
};

const REGION_TEXT = {
  North:"#c4b5fd", East:"#67e8f9", West:"#fcd34d", South:"#6ee7b7",
};

// ── Helpers ──────────────────────────────────────────────
const disp2 = (n) =>
  n !== null && n !== undefined ? Number(n).toFixed(2) : "—";

function rainIntensity(r) {
  if (r > 80) return "high";
  if (r > 30) return "med";
  return "low";
}

function heatColor(v) {
  if (v < 0.25) return "#1e3a5f";
  if (v < 0.50) return "#2563eb";
  if (v < 0.75) return "#f59e0b";
  return "#ef4444";
}

function heatTextColor(v) {
  if (v < 0.25) return "#93c5fd";
  if (v < 0.50) return "#bfdbfe";
  if (v < 0.75) return "#fef3c7";
  return "#fee2e2";
}

function getCondition(weather) {
  const rain = weather?.rainfall ?? 0;
  if (rain > 50) return "rainy";
  return "normal";
}

// ── Compute 7-day moving average ─────────────────────────
function addMA7(data, key) {
  return data.map((row, i) => {
    const slice = data.slice(Math.max(0, i - 6), i + 1);
    const avg   = slice.reduce((s, r) => s + Number(r[key] || 0), 0) / slice.length;
    return { ...row, [`${key}_ma7`]: Number(avg.toFixed(2)) };
  });
}

// ── Normalize city weather row → standard keys ───────────
function normalizeWeather(row) {
  if (!row) return null;
  return {
    ...row,
    temperature : Number(row.temperature_c  ?? 0),
    rainfall    : Number(row.rainfall_mm    ?? 0),
    humidity    : Number(row.humidity_pct   ?? 0),
    wind_speed  : Number(row.wind_speed_kmh ?? 0),
    pressure    : Number(row.pressure_hpa   ?? 0),
  };
}

// ── API helper ───────────────────────────────────────────
async function apiFetch(url) {
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  return res.json();
}

// ── Format seconds as MM:SS ──────────────────────────────
function formatCountdown(seconds) {
  const m = String(Math.floor(seconds / 60)).padStart(2, "0");
  const s = String(seconds % 60).padStart(2, "0");
  return `${m}:${s}`;
}

// ─────────────────────────────────────────────────────────
// SUB-COMPONENTS
// ─────────────────────────────────────────────────────────

function Header({ user, onLogout, lastUpdated, countdown }) {
  return (
    <div className="header glass">
      <h1>Cloudburst Identification &amp; Weather Anomaly Analysis</h1>
      <p>
        <span className="live-dot" />
        Real-time atmospheric monitoring — India regional grid
        {lastUpdated && (
          <span style={{ marginLeft:"0.6rem", opacity:0.55 }}>
            · Updated {lastUpdated}
          </span>
        )}
        {countdown !== null && (
          <span className="countdown-badge">
            ⟳ {formatCountdown(countdown)}
          </span>
        )}
      </p>
      {user && (
        <div className="header-user">
          <span className={`role-pill role-pill--${user.role}`}>{user.role}</span>
          <span className="username-text">{user.username}</span>
          <button className="logout-btn" onClick={onLogout}>Sign Out</button>
        </div>
      )}
    </div>
  );
}

function CityDropdown({ cities, selectedId, onChange }) {
  return (
    <div className="city-selector">
      <label className="city-label">📌 City</label>
      <select
        className="city-select"
        value={selectedId || ""}
        onChange={(e) => onChange(Number(e.target.value))}
      >
        {cities.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}, {c.state}
          </option>
        ))}
      </select>
    </div>
  );
}

function AlertBanner({ condition, anomalyCount }) {
  const configs = {
    normal: {
      cls:"al-normal", icon:"✔",
      title:"Normal Conditions",
      desc:"All parameters within safe thresholds.",
    },
    rainy: {
      cls:"al-rain", icon:"⚠",
      title:"Heavy Rain Alert",
      desc: anomalyCount > 0
        ? `${anomalyCount} open anomaly/anomalies require attention.`
        : "Precipitation elevated. Monitor active.",
    },
  };
  const a = configs[condition] || configs.normal;
  return (
    <div className={`alert-banner ${a.cls}`}>
      <span className="alert-icon">{a.icon}</span>
      <div>
        <strong>{a.title}</strong>
        <div className="alert-desc">{a.desc}</div>
      </div>
    </div>
  );
}

function WeatherFx({ condition }) {
  const configs = {
    normal: {
      icon:"🌐", cls:"float",
      title:"Clear skies — optimal conditions",
      desc:"No anomalies detected. Sensors nominal.",
    },
    rainy: {
      icon:"🌧", cls:"",
      title:"Heavy rainfall event in progress",
      desc:"Precipitation intensity monitored. Drainage systems active.",
    },
  };
  const f = configs[condition] || configs.normal;
  const drops = Array.from({ length:18 }, (_, i) => ({
    key:i,
    left:`${(i*5.5).toFixed(1)}%`,
    delay:`${((i*0.04)%0.7).toFixed(2)}s`,
    duration:`${(0.45+(i%4)*0.1).toFixed(2)}s`,
  }));
  return (
    <div className="weather-fx">
      {condition === "rainy" && drops.map((d) => (
        <div key={d.key} className="drop"
          style={{ left:d.left, animationDelay:d.delay, animationDuration:d.duration }}
        />
      ))}
      <div className={`fx-icon ${f.cls}`}>{f.icon}</div>
      <div className="fx-text"><h3>{f.title}</h3><p>{f.desc}</p></div>
    </div>
  );
}

function MetricCard({ icon, label, value, unit, statusCls, statusText, children }) {
  const cardCls =
    statusCls === "s-danger" ? "metric-card danger"
    : statusCls === "s-warn" ? "metric-card abnormal"
    : "metric-card";
  return (
    <div className={cardCls}>
      <div className="card-top">
        <span className="card-icon">{icon}</span>
        <span className={`card-status ${statusCls}`}>{statusText}</span>
      </div>
      <div className="card-label">{label}</div>
      <div>
        <span className="card-value">{value ?? "—"}</span>
        {unit && <span className="card-unit"> {unit}</span>}
      </div>
      {children}
    </div>
  );
}

function RainfallPips({ intensity }) {
  return (
    <div className="pip-bar">
      {["low","med","high"].map((lvl, i) => {
        const active = ["low","med","high"].indexOf(intensity) >= i;
        return <div key={lvl} className={`pip${active ? " on-"+intensity : ""}`} />;
      })}
    </div>
  );
}

function MetricsGrid({ weather, loading }) {
  if (loading && !weather) {
    return <div className="cards-loading">Loading weather data…</div>;
  }

  const temp     = weather?.temperature ?? null;
  const rain     = weather?.rainfall    ?? null;
  const hum      = weather?.humidity    ?? null;
  const wind     = weather?.wind_speed  ?? null;
  const pressure = weather?.pressure    ?? null;
  const ri       = rainIntensity(rain ?? 0);

  const tempStatus = temp > 38      ? ["s-danger","Critical"] : temp > 33    ? ["s-warn","High"]     : ["s-ok","Normal"];
  const rainStatus = ri==="high"    ? ["s-danger","High"]     : ri==="med"   ? ["s-warn","Medium"]   : ["s-ok","Low"];
  const humStatus  = hum > 85       ? ["s-warn","Very High"]  : hum < 30     ? ["s-warn","Very Dry"] : ["s-ok","Comfortable"];
  const windStatus = wind > 60      ? ["s-danger","Strong"]   : wind > 30    ? ["s-warn","Moderate"] : ["s-ok","Normal"];
  const presStatus = pressure < 990 ? ["s-warn","Low"]        : pressure > 1020 ? ["s-warn","High"]  : ["s-ok","Normal"];

  return (
    <div className="cards-grid cards-5">
      <MetricCard icon="🌡️" label="Temperature"
        value={temp !== null ? disp2(temp) : "—"} unit="°C"
        statusCls={tempStatus[0]} statusText={tempStatus[1]} />
      <MetricCard icon="🌧️" label="Rainfall"
        value={rain !== null ? disp2(rain) : "—"} unit="mm"
        statusCls={rainStatus[0]} statusText={rainStatus[1]}>
        <RainfallPips intensity={ri} />
      </MetricCard>
      <MetricCard icon="💧" label="Humidity"
        value={hum !== null ? disp2(hum) : "—"} unit="%"
        statusCls={humStatus[0]} statusText={humStatus[1]} />
      <MetricCard icon="💨" label="Wind Speed"
        value={wind !== null ? disp2(wind) : "—"} unit="km/h"
        statusCls={windStatus[0]} statusText={windStatus[1]} />
      <MetricCard icon="🔵" label="Pressure"
        value={pressure !== null ? disp2(pressure) : "—"} unit="hPa"
        statusCls={presStatus[0]} statusText={presStatus[1]} />
    </div>
  );
}

const RainfallTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <p className="tt-label">{label}</p>
      <p className="tt-value">Rainfall: {Number(payload[0]?.value).toFixed(2)} mm</p>
      {payload[1]?.value != null && (
        <p className="tt-value" style={{ color:"#fbbf24" }}>
          7-day avg: {Number(payload[1].value).toFixed(2)} mm
        </p>
      )}
    </div>
  );
};

const TempTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      <p className="tt-label">{label}</p>
      <p className="tt-value">Temp: {Number(payload[0]?.value).toFixed(1)}°C</p>
      {payload[1]?.value != null && (
        <p className="tt-value" style={{ color:"#fbbf24" }}>
          7-day avg: {Number(payload[1].value).toFixed(1)}°C
        </p>
      )}
    </div>
  );
};

function RainfallChart({ data, anomalyDates }) {
  const anomalySet = new Set(anomalyDates || []);
  return (
    <div className="chart-card">
      <div className="chart-title">Rainfall Trend — Area Chart (7-day MA)</div>
      <ResponsiveContainer width="100%" height={185}>
        <AreaChart data={data} margin={{ top:4, right:8, left:-20, bottom:0 }}>
          <defs>
            <linearGradient id="rfGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#60a5fa" stopOpacity={0.35} />
              <stop offset="95%" stopColor="#60a5fa" stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="date"
            tick={{ fill:"rgba(255,255,255,0.45)", fontSize:9 }}
            axisLine={false} tickLine={false}
            tickFormatter={(v) => v?.slice(5)} />
          <YAxis
            tick={{ fill:"rgba(255,255,255,0.45)", fontSize:10 }}
            axisLine={false} tickLine={false}
            tickFormatter={(v) => Number(v).toFixed(0)} />
          <Tooltip content={<RainfallTooltip />} />
          <Area type="monotone" dataKey="rainfall"
            stroke="#60a5fa" strokeWidth={2} fill="url(#rfGrad)"
            dot={(props) => {
              const isAnomaly = anomalySet.has(props.payload?.date);
              return isAnomaly
                ? <circle key={props.key} cx={props.cx} cy={props.cy} r={5} fill="#ef4444" stroke="#fff" strokeWidth={1.5} />
                : <circle key={props.key} cx={props.cx} cy={props.cy} r={2.5} fill="#93c5fd" strokeWidth={0} />;
            }} />
          <Line type="monotone" dataKey="rainfall_ma7"
            stroke="#fbbf24" strokeWidth={1.5} strokeDasharray="4 2" dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function TempChart({ data, anomalyDates }) {
  const anomalySet = new Set(anomalyDates || []);
  return (
    <div className="chart-card">
      <div className="chart-title">Temperature Variation — Line Chart (7-day MA)</div>
      <ResponsiveContainer width="100%" height={185}>
        <LineChart data={data} margin={{ top:4, right:8, left:-20, bottom:0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="date"
            tick={{ fill:"rgba(255,255,255,0.45)", fontSize:9 }}
            axisLine={false} tickLine={false}
            tickFormatter={(v) => v?.slice(5)} />
          <YAxis
            tick={{ fill:"rgba(255,255,255,0.45)", fontSize:10 }}
            axisLine={false} tickLine={false}
            tickFormatter={(v) => Number(v).toFixed(0)} />
          <Tooltip content={<TempTooltip />} />
          <Line type="monotone" dataKey="temperature"
            stroke="#fb923c" strokeWidth={2} strokeDasharray="5 3"
            dot={(props) => {
              const isAnomaly = anomalySet.has(props.payload?.date);
              return isAnomaly
                ? <circle key={props.key} cx={props.cx} cy={props.cy} r={5} fill="#ef4444" stroke="#fff" strokeWidth={1.5} />
                : <circle key={props.key} cx={props.cx} cy={props.cy} r={2.5} fill="#fdba74" strokeWidth={0} />;
            }} />
          <Line type="monotone" dataKey="temperature_ma7"
            stroke="#fbbf24" strokeWidth={1.5} strokeDasharray="4 2" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function HeatmapCell({ city, anomalyCount, maxCount }) {
  const v  = maxCount > 0 ? Math.min(1, anomalyCount / maxCount) : 0;
  const bg = heatColor(v);
  const tc = heatTextColor(v);
  const rc = REGION_TEXT[CITY_REGION[city.name]] || "#fff";
  return (
    <div className="hm-cell"
      style={{ background:bg, opacity:0.65 + v*0.35 }}
      title={`${city.name} (${city.state}) — Rainfall: ${city.rainfall_mm} mm`}
    >
      <span className="hm-region" style={{ color:rc }}>
        {CITY_REGION[city.name] || "—"}
      </span>
      <span className="hm-city" style={{ color:tc }}>{city.name}</span>
      <span className="hm-val"  style={{ color:tc }}>
        {Number(city.rainfall_mm || 0).toFixed(1)} mm
      </span>
    </div>
  );
}

function Heatmap({ overviewData }) {
  const display  = overviewData.slice(0, 12);
  const maxRain  = Math.max(1, ...display.map((c) => Number(c.rainfall_mm || 0)));
  return (
    <div className="chart-card full">
      <div className="chart-title">Regional Sensor Heatmap — Rainfall Grid (Top 12 Cities)</div>
      <div className="hm-section-label">Latest rainfall · North · East · West · South India</div>
      <div className="heatmap-outer">
        <div className="heatmap-grid">
          {display.map((city, i) => (
            <HeatmapCell
              key={city.city_name || i}
              city={{ name: city.city_name, state: city.state, rainfall_mm: city.rainfall_mm }}
              anomalyCount={Number(city.rainfall_mm || 0)}
              maxCount={maxRain}
            />
          ))}
        </div>
      </div>
      <div className="hm-legend">
        {[["#1e3a5f","Low"],["#2563eb","Moderate"],["#f59e0b","High"],["#ef4444","Critical"]].map(
          ([bg, lbl]) => (
            <span key={lbl}>
              <span className="hm-swatch" style={{ background:bg }} />
              {lbl}
            </span>
          )
        )}
      </div>
    </div>
  );
}

function AnomalyPanel({ anomalies, user, onAcknowledge }) {
  const canAct =
    user?.role?.toLowerCase() === "admin" ||
    user?.role?.toLowerCase() === "analyst";

  return (
    <div className="chart-card full anomaly-panel">
      <div className="chart-title">Recent Open Anomalies</div>
      {anomalies.length === 0 ? (
        <p className="no-anomalies">✔ No open anomalies at this time.</p>
      ) : (
        <div className="anomaly-list">
          {anomalies.map((a) => (
            <div key={a.id}
              className={`anomaly-row ${a.deviation_type === "HIGH" ? "anom-high" : "anom-low"}`}
            >
              <div className="anom-left">
                <span className={`anom-badge ${a.deviation_type === "HIGH" ? "badge-high" : "badge-low"}`}>
                  {a.deviation_type}
                </span>
                <span className="anom-city">{a.city_name}</span>
                <span className="anom-param">{a.parameter?.replace(/_/g," ")}</span>
                <span className="anom-val">{disp2(a.observed_value)}</span>
              </div>
              <div className="anom-right">
                <span className="anom-date">{a.detected_date}</span>
                {canAct && a.status === "open" && (
                  <button className="ack-btn" onClick={() => onAcknowledge(a.id)}>
                    Acknowledge
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// MAIN APP
// ─────────────────────────────────────────────────────────

const REFRESH_SECONDS = 10 * 60; // 10 minutes

export default function App() {
  const [user,            setUser]            = useState(null);
  const [cities,          setCities]          = useState([]);
  const [selectedCityId,  setSelectedCityId]  = useState(null);
  const [latestWeather,   setLatestWeather]   = useState(null);
  const [historyData,     setHistoryData]     = useState([]);
  const [overviewData,    setOverviewData]    = useState([]);
  const [recentAnomalies, setRecentAnomalies] = useState([]);
  const [anomalyDates,    setAnomalyDates]    = useState([]);
  const [loading,         setLoading]         = useState(false);
  const [lastUpdated,     setLastUpdated]     = useState(null);
  const [countdown,       setCountdown]       = useState(null);

  const refreshRef   = useRef(null);
  const countdownRef = useRef(null);

  // ── load cities after login ──────────────────────────
  useEffect(() => {
    if (!user) return;
    apiFetch("/api/weather/cities")
      .then((data) => {
        const list = (Array.isArray(data) ? data : []).map((c) => ({
          id   : c.id,
          name : c.city_name,
          state: c.state,
        }));
        setCities(list);
        if (list.length) setSelectedCityId(list[0].id);
      })
      .catch(console.error);
  }, [user]);

  // ── fetch dashboard data for selected city ───────────
  const fetchDashboard = useCallback(async (cityId) => {
    if (!cityId) return;
    setLoading(true);
    try {
      const historyRaw = await apiFetch(`/api/weather/city/${cityId}?days=400`);
      const rawLatest  = Array.isArray(historyRaw) && historyRaw.length
        ? historyRaw[0] : null;
      setLatestWeather(normalizeWeather(rawLatest));

      const historyRaw30  = historyRaw.slice(0, 30);
      const historyMapped = (Array.isArray(historyRaw30) ? historyRaw30 : [])
        .map((r) => ({
          date       : r.date,
          rainfall   : Number(r.rainfall_mm   ?? 0),
          temperature: Number(r.temperature_c ?? 0),
        }))
        .reverse();

      const withMA = addMA7(addMA7(historyMapped, "rainfall"), "temperature");
      setHistoryData(withMA);

      const heatmapRaw = await apiFetch("/api/weather/heatmap");
      setOverviewData(Array.isArray(heatmapRaw) ? heatmapRaw : []);

      const anomRaw  = await apiFetch("/api/anomalies/recent?limit=20");
      const anomList = Array.isArray(anomRaw) ? anomRaw : [];
      setRecentAnomalies(anomList.filter((a) => a.status === "open"));

      const cityAnomRaw  = await apiFetch("/api/anomalies/recent?limit=500");
      const cityAnomList = Array.isArray(cityAnomRaw) ? cityAnomRaw : [];
      setAnomalyDates(
        cityAnomList
          .filter((a) => a.city_id === cityId)
          .map((a) => a.detected_date)
      );

      setLastUpdated(new Date().toLocaleTimeString());

      // Reset countdown to full 10 minutes after every fetch
      setCountdown(REFRESH_SECONDS);
    } catch (err) {
      console.error("Dashboard fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── re-fetch when city changes ───────────────────────
  useEffect(() => {
    if (selectedCityId) fetchDashboard(selectedCityId);
  }, [selectedCityId, fetchDashboard]);

  // ── auto-refresh every 10 minutes ───────────────────
  useEffect(() => {
    if (!user || !selectedCityId) return;

    // Clear any existing timers
    clearInterval(refreshRef.current);
    clearInterval(countdownRef.current);

    // Main refresh interval — 10 minutes
    refreshRef.current = setInterval(() => {
      fetchDashboard(selectedCityId);
    }, REFRESH_SECONDS * 1000);

    // Countdown ticker — every 1 second
    countdownRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev === null || prev <= 1) return REFRESH_SECONDS;
        return prev - 1;
      });
    }, 1000);

    return () => {
      clearInterval(refreshRef.current);
      clearInterval(countdownRef.current);
    };
  }, [user, selectedCityId, fetchDashboard]);

  // ── clear timers on logout ───────────────────────────
  const handleLogout = async () => {
    clearInterval(refreshRef.current);
    clearInterval(countdownRef.current);
    try {
      await fetch("/api/auth/logout", { method:"POST", credentials:"include" });
    } catch (_) {}
    setUser(null);
    setCities([]);
    setSelectedCityId(null);
    setLatestWeather(null);
    setHistoryData([]);
    setOverviewData([]);
    setRecentAnomalies([]);
    setLastUpdated(null);
    setCountdown(null);
  };

  // ── acknowledge anomaly ──────────────────────────────
  const handleAcknowledge = async (anomalyId) => {
    try {
      await fetch(`/api/anomalies/${anomalyId}/acknowledge`, {
        method     : "POST",
        credentials: "include",
      });
      setRecentAnomalies((prev) => prev.filter((a) => a.id !== anomalyId));
    } catch (err) {
      console.error("Acknowledge error:", err);
    }
  };

  if (!user) return <Login onLoginSuccess={(u) => setUser(u)} />;

  const condition     = getCondition(latestWeather);
  const openAnomalies = recentAnomalies.filter((a) => a.status === "open");

  return (
    <div className={`dash ${condition}`}>
      <Header
        user={user}
        onLogout={handleLogout}
        lastUpdated={lastUpdated}
        countdown={countdown}
      />

      <CityDropdown
        cities={cities}
        selectedId={selectedCityId}
        onChange={(id) => {
          setSelectedCityId(id);
          setCountdown(REFRESH_SECONDS);   // reset countdown on city change
        }}
      />
      <PdfButton
        cityId={selectedCityId}
        cityName={cities.find((c) => c.id === selectedCityId)?.name}
        userRole={user?.role}
      />

      <AlertBanner condition={condition} anomalyCount={openAnomalies.length} />
      <WeatherFx   condition={condition} />
      <MetricsGrid weather={latestWeather} loading={loading} />

      <div className="charts-grid">
        <RainfallChart data={historyData} anomalyDates={anomalyDates} />
        <TempChart     data={historyData} anomalyDates={anomalyDates} />
        <Heatmap       overviewData={overviewData} />
        <AnomalyPanel
          anomalies={openAnomalies}
          user={user}
          onAcknowledge={handleAcknowledge}
        />
      </div>

      {(user?.role === "admin" || user?.role === "analyst") && (
        <AnomalyList />
      )}

      <footer className="dash-footer">
        Cloudburst Analytics Engine · 35-City India Sensor Grid v3.0
        · Auto-refresh every 10 min
      </footer>
    </div>
  );
}
