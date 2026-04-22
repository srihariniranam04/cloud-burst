# ============================================================
# modules/pdf_generator.py
# Cloud Burst Detection System — PDF Report Generator
# Uses ReportLab to generate cloudburst reports
# Triggered manually when cloudburst is identified
# ============================================================

import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from modules.db import db
from config import Config
from sqlalchemy import text


# ============================================================
# GENERATE PDF REPORT FOR ONE CLOUDBURST EVENT
# ============================================================

def generate_cloudburst_report(cloudburst_id, generated_by):
    """
    Generates a PDF report for a confirmed cloudburst event.

    Args:
        cloudburst_id: int — ID from cloudbursts table
        generated_by:  int — user_id who triggered generation

    Returns:
        dict: { success, file_path, filename }
    """
    print(f"[{datetime.now()}] Generating PDF for "
          f"cloudburst ID {cloudburst_id}...")

    # --- Fetch cloudburst data ---
    cb_data = _fetch_cloudburst_data(cloudburst_id)
    if not cb_data:
        return {
            "success":   False,
            "message":   "Cloudburst not found",
            "file_path": None
        }

    # --- Fetch anomalies for same city + date ---
    anomalies = _fetch_anomalies(
        cb_data["city_id"],
        cb_data["date"]
    )

    # --- Fetch 7 day weather history ---
    history = _fetch_weather_history(
        cb_data["city_id"],
        cb_data["date"]
    )

    # --- Build filename ---
    filename = (
        f"cloudburst_report_"
        f"{cb_data['city_name'].replace(' ', '_')}_"
        f"{cb_data['date']}_"
        f"{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    )

    # --- Ensure reports directory exists ---
    os.makedirs(Config.REPORTS_DIR, exist_ok=True)
    file_path = os.path.join(Config.REPORTS_DIR, filename)

    # --- Build PDF ---
    try:
        _build_pdf(file_path, cb_data, anomalies, history)
    except Exception as e:
        print(f"  [ERROR] PDF generation failed: {str(e)}")
        return {
            "success":   False,
            "message":   str(e),
            "file_path": None
        }

    # --- Save record to pdf_reports table ---
    _save_pdf_record(
        cloudburst_id = cloudburst_id,
        filename      = filename,
        file_path     = file_path,
        generated_by  = generated_by
    )

    print(f"  ✓ PDF saved: {filename}")
    return {
        "success":   True,
        "file_path": file_path,
        "filename":  filename
    }


# ============================================================
# BUILD THE ACTUAL PDF DOCUMENT
# ============================================================

def _build_pdf(file_path, cb_data, anomalies, history):
    """Builds the PDF using ReportLab Platypus."""

    doc    = SimpleDocTemplate(
        file_path,
        pagesize    = A4,
        rightMargin = 0.75 * inch,
        leftMargin  = 0.75 * inch,
        topMargin   = 0.75 * inch,
        bottomMargin= 0.75 * inch
    )
    styles = getSampleStyleSheet()
    story  = []

    # --- Custom Styles ---
    title_style = ParagraphStyle(
        "TitleStyle",
        parent    = styles["Title"],
        fontSize  = 18,
        textColor = colors.HexColor("#1a237e"),
        alignment = TA_CENTER,
        spaceAfter= 6
    )

    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent    = styles["Normal"],
        fontSize  = 10,
        textColor = colors.HexColor("#555555"),
        alignment = TA_CENTER,
        spaceAfter= 4
    )

    section_style = ParagraphStyle(
        "SectionStyle",
        parent    = styles["Heading2"],
        fontSize  = 12,
        textColor = colors.HexColor("#1a237e"),
        spaceBefore=12,
        spaceAfter= 4
    )

    normal_style = ParagraphStyle(
        "NormalStyle",
        parent    = styles["Normal"],
        fontSize  = 10,
        spaceAfter= 4
    )

    # --- Title ---
    story.append(Paragraph(
        "Cloud Burst Identification &amp; Weather Anomaly Detection System",
        title_style
    ))
    story.append(Paragraph(
        "Official Cloudburst Event Report",
        subtitle_style
    ))
    story.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}",
        subtitle_style
    ))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor("#1a237e")
    ))
    story.append(Spacer(1, 12))

    # --- Event Summary ---
    story.append(Paragraph("1. Event Summary", section_style))

    summary_data = [
        ["Field",           "Details"],
        ["City",            cb_data["city_name"]],
        ["State",           cb_data.get("state", "India")],
        ["Date",            str(cb_data["date"])],
        ["Rainfall",        f"{cb_data['rainfall']} mm"],
        ["Dynamic Threshold", f"{cb_data['threshold']} mm"],
        ["Spike Delta",     f"{cb_data['delta']} mm"],
        ["Spike %",         f"{cb_data['percent_change']}%"],
        ["Status",          cb_data["status"]],
        ["Report ID",       str(cb_data["id"])],
    ]

    summary_table = Table(summary_data, colWidths=[2.5*inch, 4*inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#1a237e")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 10),
        ("BACKGROUND",  (0, 1), (0, -1), colors.HexColor("#e8eaf6")),
        ("FONTNAME",    (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 1), (-1, -1), 9),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.white, colors.HexColor("#f5f5f5")]),
        ("PADDING",     (0, 0), (-1, -1), 6),
    ]))

    story.append(summary_table)
    story.append(Spacer(1, 12))

    # --- Anomalies Detected ---
    story.append(Paragraph("2. Anomalies Detected on Same Date", section_style))

    if anomalies:
        anomaly_data = [
            ["Parameter", "Recorded Value", "Anomaly Type"]
        ]
        for a in anomalies:
            anomaly_data.append([
                a["parameter"].replace("_", " ").title(),
                str(a["value"]),
                a["anomaly_type"]
            ])

        anomaly_table = Table(
            anomaly_data,
            colWidths=[2*inch, 2.5*inch, 2*inch]
        )
        anomaly_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#b71c1c")),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 9),
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                [colors.white, colors.HexColor("#ffebee")]),
            ("PADDING",     (0, 0), (-1, -1), 6),
        ]))
        story.append(anomaly_table)
    else:
        story.append(Paragraph(
            "No additional anomalies detected on this date.",
            normal_style
        ))

    story.append(Spacer(1, 12))

    # --- 7 Day Weather History ---
    story.append(Paragraph("3. 7-Day Weather History", section_style))

    if history:
        history_data = [
            ["Date", "Rainfall (mm)", "Temp (°C)",
             "Humidity (%)", "Wind (kmh)", "Pressure (hPa)"]
        ]
        for h in history:
            history_data.append([
                str(h["date"]),
                str(h["rainfall"]  or "-"),
                str(h["temperature"] or "-"),
                str(h["humidity"]  or "-"),
                str(h["wind_speed"]or "-"),
                str(h["pressure"]  or "-")
            ])

        history_table = Table(
            history_data,
            colWidths=[1.2*inch, 1.2*inch, 1*inch,
                       1.2*inch, 1*inch, 1.2*inch]
        )
        history_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#1565c0")),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 8),
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                [colors.white, colors.HexColor("#e3f2fd")]),
            ("PADDING",     (0, 0), (-1, -1), 5),
        ]))
        story.append(history_table)
    else:
        story.append(Paragraph(
            "No historical data available for this city.",
            normal_style
        ))

    story.append(Spacer(1, 12))

    # --- Footer ---
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor("#cccccc")
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This report was automatically generated by the Cloud Burst "
        "Identification and Weather Anomaly Detection System. "
        "Data source: Visual Crossing Weather API.",
        ParagraphStyle(
            "FooterStyle",
            parent    = styles["Normal"],
            fontSize  = 8,
            textColor = colors.HexColor("#888888"),
            alignment = TA_CENTER
        )
    ))

    doc.build(story)


# ============================================================
# FETCH CLOUDBURST DATA FROM DB
# ============================================================

def _fetch_cloudburst_data(cloudburst_id):
    """Fetches full cloudburst details from DB."""
    query = text("""
        SELECT
            cb.id, cb.city_id, cb.date,
            cb.rainfall, cb.threshold,
            cb.delta, cb.percent_change,
            cb.status,
            c.name  as city_name,
            c.state as state
        FROM cloudbursts cb
        JOIN cities c ON cb.city_id = c.id
        WHERE cb.id = :cloudburst_id
    """)

    with db.engine.connect() as conn:
        row = conn.execute(
            query, {"cloudburst_id": cloudburst_id}
        ).fetchone()

    if not row:
        return None

    return {
        "id":             row[0],
        "city_id":        row[1],
        "date":           row[2],
        "rainfall":       row[3],
        "threshold":      row[4],
        "delta":          row[5],
        "percent_change": row[6],
        "status":         row[7],
        "city_name":      row[8],
        "state":          row[9]
    }


# ============================================================
# FETCH ANOMALIES FOR SAME CITY + DATE
# ============================================================

def _fetch_anomalies(city_id, date):
    """Fetches all anomalies for a city on a given date."""
    query = text("""
        SELECT parameter, value, anomaly_type
        FROM anomalies
        WHERE city_id = :city_id
          AND date    = :date
    """)

    with db.engine.connect() as conn:
        rows = conn.execute(query, {
            "city_id": city_id,
            "date":    date
        }).fetchall()

    return [
        {
            "parameter":    row[0],
            "value":        row[1],
            "anomaly_type": row[2]
        }
        for row in rows
    ]


# ============================================================
# FETCH 7 DAY WEATHER HISTORY
# ============================================================

def _fetch_weather_history(city_id, date):
    """Fetches last 7 days of weather data for a city."""
    query = text("""
        SELECT
            date, rainfall, temperature,
            humidity, wind_speed, pressure
        FROM weather_data
        WHERE city_id = :city_id
          AND date   <= :date
        ORDER BY date DESC
        LIMIT 7
    """)

    with db.engine.connect() as conn:
        rows = conn.execute(query, {
            "city_id": city_id,
            "date":    date
        }).fetchall()

    return [
        {
            "date":        row[0],
            "rainfall":    row[1],
            "temperature": row[2],
            "humidity":    row[3],
            "wind_speed":  row[4],
            "pressure":    row[5]
        }
        for row in rows
    ]


# ============================================================
# SAVE PDF RECORD TO pdf_reports TABLE
# ============================================================

def _save_pdf_record(cloudburst_id, filename,
                     file_path, generated_by):
    """Saves PDF generation record to pdf_reports table."""
    query = text("""
        INSERT INTO pdf_reports
            (cloudburst_id, filename, file_path,
             generated_by, generated_at)
        VALUES
            (:cloudburst_id, :filename, :file_path,
             :generated_by, NOW())
    """)

    try:
        with db.engine.connect() as conn:
            conn.execute(query, {
                "cloudburst_id": cloudburst_id,
                "filename":      filename,
                "file_path":     file_path,
                "generated_by":  generated_by
            })
            conn.commit()
            
    except Exception as e:
        print(f"  [LOG ERROR] Could not save PDF record: {str(e)}")
# ============================================================
# GENERATE_PDF — General report wrapper called by routes/reports.py
# ============================================================

def generate_pdf(payload):
    # 4 spaces — function body
    city_name   = payload['city_name'].replace(' ', '_')
    report_type = payload['report_type']
    start_date  = payload['start_date']
    end_date    = payload['end_date']

    file_name = (
        f"report_{city_name}_{report_type}_"
        f"{start_date}_to_{end_date}_"
        f"{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    )

    os.makedirs(Config.REPORTS_DIR, exist_ok=True)
    file_path = os.path.join(Config.REPORTS_DIR, file_name)

    _build_general_pdf(file_path, payload)

    file_size_kb = round(os.path.getsize(file_path) / 1024, 1)

    return {
        "file_path":    file_path,
        "file_name":    file_name,
        "file_size_kb": file_size_kb
    }


def _build_general_pdf(file_path, payload):
    # 4 spaces — function body
    doc = SimpleDocTemplate(
        file_path,
        pagesize     = A4,
        rightMargin  = 0.75 * inch,
        leftMargin   = 0.75 * inch,
        topMargin    = 0.75 * inch,
        bottomMargin = 0.75 * inch
    )
    styles = getSampleStyleSheet()
    story  = []

    # ── styles ───────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "TitleStyle",
        parent    = styles["Title"],
        fontSize  = 18,
        textColor = colors.HexColor("#1a237e"),
        alignment = TA_CENTER,
        spaceAfter= 6
    )
    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent    = styles["Normal"],
        fontSize  = 10,
        textColor = colors.HexColor("#555555"),
        alignment = TA_CENTER,
        spaceAfter= 4
    )
    section_style = ParagraphStyle(
        "SectionStyle",
        parent     = styles["Heading2"],
        fontSize   = 12,
        textColor  = colors.HexColor("#1a237e"),
        spaceBefore= 12,
        spaceAfter = 4
    )
    normal_style = ParagraphStyle(
        "NormalStyle",
        parent    = styles["Normal"],
        fontSize  = 10,
        spaceAfter= 4
    )

    # ── header ───────────────────────────────────────────────────
    story.append(Paragraph(
        "Cloud Burst Identification &amp; Weather Anomaly Detection System",
        title_style
    ))
    story.append(Paragraph(
        f"{payload['report_type'].capitalize()} Weather Report — "
        f"{payload['city_name']}, {payload.get('state_name', 'India')}",
        subtitle_style
    ))
    story.append(Paragraph(
        f"Period: {payload['start_date']}  to  {payload['end_date']}",
        subtitle_style
    ))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}",
        subtitle_style
    ))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor("#1a237e")
    ))
    story.append(Spacer(1, 12))

    # ── section 1: weather data ───────────────────────────────────
    story.append(Paragraph("1. Daily Weather Data", section_style))

    weather_rows = payload.get('weather_data', [])
    if weather_rows:
        # 8 spaces — inside if block
        table_data = [[
            "Date", "Rainfall\n(mm)", "Temp\n(°C)",
            "Humidity\n(%)", "Wind\n(kmh)", "Pressure\n(hPa)", "Wind Dir"
        ]]
        for w in weather_rows:
            # 12 spaces — inside for loop
            table_data.append([
                str(w.get('record_date',    '-')),
                str(w.get('rainfall_mm',    '-')),
                str(w.get('temperature_c',  '-')),
                str(w.get('humidity_pct',   '-')),
                str(w.get('wind_speed_kmh', '-')),
                str(w.get('pressure_hpa',   '-')),
                str(w.get('wind_direction', '-')),
            ])

        t = Table(table_data, colWidths=[
            1*inch, 0.9*inch, 0.8*inch,
            0.9*inch, 0.8*inch, 0.9*inch, 0.8*inch
        ])
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), colors.HexColor("#1565c0")),
            ("TEXTCOLOR",      (0, 0), (-1, 0), colors.white),
            ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",       (0, 0), (-1, -1), 8),
            ("ALIGN",          (0, 0), (-1, -1), "CENTER"),
            ("GRID",           (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                [colors.white, colors.HexColor("#e3f2fd")]),
            ("PADDING",        (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
    else:
        # 8 spaces — else block
        story.append(Paragraph("No weather data for this period.", normal_style))

    story.append(Spacer(1, 12))

    # ── section 2: cloudbursts ────────────────────────────────────
    story.append(Paragraph("2. Cloudburst Events", section_style))

    cb_rows = payload.get('cloudbursts', [])
    if cb_rows:
        table_data = [[
            "Date", "Rainfall\n(mm)", "Threshold\n(mm)",
            "Spike Δ\n(mm)", "Spike\n(%)", "Status"
        ]]
        for cb in cb_rows:
            table_data.append([
                str(cb.get('event_date',      '-')),
                str(cb.get('rainfall_mm',     '-')),
                str(cb.get('threshold_used',  '-')),
                str(cb.get('spike_delta',     '-')),
                str(cb.get('spike_percent',   '-')),
                str(cb.get('status',          '-')),
            ])

        t = Table(table_data, colWidths=[
            1.1*inch, 1*inch, 1.1*inch,
            1*inch, 0.9*inch, 1.1*inch
        ])
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), colors.HexColor("#b71c1c")),
            ("TEXTCOLOR",      (0, 0), (-1, 0), colors.white),
            ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",       (0, 0), (-1, -1), 8),
            ("ALIGN",          (0, 0), (-1, -1), "CENTER"),
            ("GRID",           (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                [colors.white, colors.HexColor("#ffebee")]),
            ("PADDING",        (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
    else:
        story.append(Paragraph(
            "No cloudburst events recorded in this period.", normal_style
        ))

    story.append(Spacer(1, 12))

    # ── section 3: anomalies ──────────────────────────────────────
    story.append(Paragraph("3. Anomalies Detected", section_style))

    anomaly_rows = payload.get('anomalies', [])
    if anomaly_rows:
        table_data = [[
            "Date", "Parameter", "Observed\nValue",
            "Mean", "Std Dev", "Deviation\nScore", "Type"
        ]]
        for a in anomaly_rows:
            table_data.append([
                str(a.get('detected_date',   '-')),
                str(a.get('parameter',       '-')).replace('_', ' ').title(),
                str(a.get('observed_value',  '-')),
                str(a.get('mean_value',      '-')),
                str(a.get('std_dev',         '-')),
                str(a.get('deviation_score', '-')),
                str(a.get('anomaly_type',    '-')),
            ])

        t = Table(table_data, colWidths=[
            1*inch, 1.1*inch, 0.9*inch,
            0.8*inch, 0.8*inch, 0.9*inch, 0.7*inch
        ])
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), colors.HexColor("#4a148c")),
            ("TEXTCOLOR",      (0, 0), (-1, 0), colors.white),
            ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",       (0, 0), (-1, -1), 8),
            ("ALIGN",          (0, 0), (-1, -1), "CENTER"),
            ("GRID",           (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                [colors.white, colors.HexColor("#f3e5f5")]),
            ("PADDING",        (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
    else:
        story.append(Paragraph(
            "No anomalies detected in this period.", normal_style
        ))

    story.append(Spacer(1, 12))

    # ── footer ────────────────────────────────────────────────────
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor("#cccccc")
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Auto-generated by Cloud Burst Identification and Weather Anomaly "
        "Detection System. Data source: Visual Crossing Weather API.",
        ParagraphStyle(
            "FooterStyle",
            parent    = styles["Normal"],
            fontSize  = 8,
            textColor = colors.HexColor("#888888"),
            alignment = TA_CENTER
        )
    ))

    doc.build(story)