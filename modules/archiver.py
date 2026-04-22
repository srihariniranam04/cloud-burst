# ============================================================
# modules/archiver.py
# Cloud Burst Detection System — Nightly Archive Job
# Moves data older than 5 years from weather_data
# to weather_archive table
# Runs automatically every night
# ============================================================

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from modules.db import db
from sqlalchemy import text


# ============================================================
# MAIN ARCHIVE JOB
# Called once nightly via scheduler
# ============================================================

def run_archive_job():
    """
    Moves weather records older than 5 years from
    weather_data table to weather_archive table.

    Flow:
        1. Calculate cutoff date (today minus 5 years)
        2. Copy old records to weather_archive
        3. Delete copied records from weather_data
        4. Log summary
    """
    print(f"[{datetime.now()}] Starting nightly archive job...")

    cutoff_date = datetime.now().date() - relativedelta(years=5)
    print(f"  Archiving records older than: {cutoff_date}")

    # --- Step 1: Count records to archive ---
    count_query = text("""
        SELECT COUNT(*) FROM weather_data
        WHERE date < :cutoff_date
    """)

    with db.engine.connect() as conn:
        count = conn.execute(
            count_query, {"cutoff_date": cutoff_date}
        ).scalar()

    if count == 0:
        print(f"  No records to archive. Job complete.")
        return {
            "archived": 0,
            "deleted":  0,
            "status":   "nothing_to_archive"
        }

    print(f"  Found {count} records to archive...")

    # --- Step 2: Copy old records to weather_archive ---
    copy_query = text("""
        INSERT IGNORE INTO weather_archive
            (city_id, date, temperature, temp_max, temp_min,
             humidity, rainfall, wind_speed, wind_direction,
             pressure, archived_at)
        SELECT
            city_id, date, temperature, temp_max, temp_min,
            humidity, rainfall, wind_speed, wind_direction,
            pressure, NOW()
        FROM weather_data
        WHERE date < :cutoff_date
    """)

    with db.engine.connect() as conn:
        result = conn.execute(
            copy_query, {"cutoff_date": cutoff_date}
        )
        copied = result.rowcount
        conn.commit()

    print(f"  Copied {copied} records to weather_archive.")

    # --- Step 3: Delete archived records from weather_data ---
    delete_query = text("""
        DELETE FROM weather_data
        WHERE date < :cutoff_date
    """)

    with db.engine.connect() as conn:
        result = conn.execute(
            delete_query, {"cutoff_date": cutoff_date}
        )
        deleted = result.rowcount
        conn.commit()

    print(f"  Deleted {deleted} records from weather_data.")
    print(f"[{datetime.now()}] Archive job complete.")
    print(f"  Archived : {copied}")
    print(f"  Deleted  : {deleted}")

    return {
        "archived":    copied,
        "deleted":     deleted,
        "cutoff_date": str(cutoff_date),
        "status":      "success"
    }


# ============================================================
# VERIFY ARCHIVE INTEGRITY
# Checks that all archived records exist in weather_archive
# before deleting from weather_data
# ============================================================

def verify_archive_integrity(cutoff_date):
    """
    Verifies that records copied to weather_archive
    match what was in weather_data before deletion.

    Returns:
        dict: { match, weather_data_count, archive_count }
    """
    source_query = text("""
        SELECT COUNT(*) FROM weather_data
        WHERE date < :cutoff_date
    """)

    archive_query = text("""
        SELECT COUNT(*) FROM weather_archive
        WHERE date < :cutoff_date
    """)

    with db.engine.connect() as conn:
        source_count  = conn.execute(
            source_query,  {"cutoff_date": cutoff_date}
        ).scalar()
        archive_count = conn.execute(
            archive_query, {"cutoff_date": cutoff_date}
        ).scalar()

    match = source_count == archive_count

    return {
        "match":              match,
        "weather_data_count": source_count,
        "archive_count":      archive_count
    }


# ============================================================
# GET ARCHIVE STATISTICS
# Used by admin dashboard to show archive status
# ============================================================

def get_archive_stats():
    """
    Returns statistics about archived vs active data.

    Returns:
        dict: { active_records, archived_records,
                oldest_active, oldest_archive }
    """
    query = text("""
        SELECT
            (SELECT COUNT(*) FROM weather_data)    as active_count,
            (SELECT COUNT(*) FROM weather_archive) as archive_count,
            (SELECT MIN(date) FROM weather_data)   as oldest_active,
            (SELECT MIN(date) FROM weather_archive)as oldest_archive,
            (SELECT MAX(date) FROM weather_data)   as newest_active
    """)

    with db.engine.connect() as conn:
        row = conn.execute(query).fetchone()

    return {
        "active_records":   row[0],
        "archived_records": row[1],
        "oldest_active":    str(row[2]) if row[2] else None,
        "oldest_archive":   str(row[3]) if row[3] else None,
        "newest_active":    str(row[4]) if row[4] else None
    }


# ============================================================
# RESTORE FROM ARCHIVE
# Moves records back from archive to main table
# Use only if needed — admin function
# ============================================================

def restore_from_archive(city_id, start_date, end_date):
    """
    Restores archived records back to weather_data.
    Admin only — use when historical data is needed.

    Args:
        city_id:    int
        start_date: date
        end_date:   date

    Returns:
        dict: { restored, status }
    """
    print(f"[{datetime.now()}] Restoring archive for "
          f"city {city_id} from {start_date} to {end_date}...")

    # Copy back to weather_data
    restore_query = text("""
        INSERT IGNORE INTO weather_data
            (city_id, date, temperature, temp_max, temp_min,
             humidity, rainfall, wind_speed, wind_direction,
             pressure, created_at)
        SELECT
            city_id, date, temperature, temp_max, temp_min,
            humidity, rainfall, wind_speed, wind_direction,
            pressure, NOW()
        FROM weather_archive
        WHERE city_id  = :city_id
          AND date    >= :start_date
          AND date    <= :end_date
    """)

    with db.engine.connect() as conn:
        result = conn.execute(restore_query, {
            "city_id":    city_id,
            "start_date": start_date,
            "end_date":   end_date
        })
        restored = result.rowcount
        conn.commit()

    print(f"  Restored {restored} records.")

    return {
        "restored": restored,
        "status":   "success"
    }