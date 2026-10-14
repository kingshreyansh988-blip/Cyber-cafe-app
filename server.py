"""FastAPI Web Server for Cyber Cafe Management Application."""
import os
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3

from database import init_db, get_db_connection, generate_job_no

app = FastAPI(title="Cyber Cafe Management Portal", version="1.0.0")

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()


# Pydantic models for request validation
class JobCreate(BaseModel):
    customer_name: str
    customer_phone: str
    service_category: str
    service_details: Optional[str] = ""
    status: Optional[str] = "Pending"
    total_amount: float
    paid_amount: float = 0.0
    payment_mode: Optional[str] = "Cash"
    notes: Optional[str] = ""


class JobUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    service_category: Optional[str] = None
    service_details: Optional[str] = None
    status: Optional[str] = None
    total_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    payment_mode: Optional[str] = None
    notes: Optional[str] = None


class SettingsUpdate(BaseModel):
    shop_name: str
    owner_name: str
    phone: str
    upi_id: str
    address: str
    tagline: Optional[str] = ""
    receipt_footer: Optional[str] = ""


# --- API Endpoints ---

@app.get("/api/settings")
def get_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


@app.post("/api/settings")
def update_settings(payload: SettingsUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    data = payload.dict()
    for k, v in data.items():
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Settings updated successfully"}


@app.get("/api/jobs")
def list_jobs(
    search: Optional[str] = None,
    status: Optional[str] = None,
    due_only: Optional[bool] = False
):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if search:
        search_term = f"%{search.strip()}%"
        query += " AND (customer_name LIKE ? OR customer_phone LIKE ? OR job_no LIKE ? OR service_details LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term])

    if status and status != "All":
        query += " AND status = ?"
        params.append(status)

    if due_only:
        query += " AND due_amount > 0"

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


@app.post("/api/jobs")
def create_job(payload: JobCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    job_no = generate_job_no()
    total = max(0.0, float(payload.total_amount))
    paid = max(0.0, float(payload.paid_amount))
    due = max(0.0, round(total - paid, 2))

    if due == 0 and total > 0:
        payment_status = "Paid"
    elif paid > 0 and due > 0:
        payment_status = "Partial"
    else:
        payment_status = "Unpaid"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO jobs (
        job_no, customer_name, customer_phone, service_category, service_details,
        status, total_amount, paid_amount, due_amount, payment_mode, payment_status,
        notes, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_no, payload.customer_name.strip(), payload.customer_phone.strip(),
        payload.service_category, payload.service_details or "", payload.status or "Pending",
        total, paid, due, payload.payment_mode or "Cash", payment_status,
        payload.notes or "", now_str, now_str
    ))

    job_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    new_job = dict(cursor.fetchone())
    conn.close()

    return new_job


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return dict(row)


@app.put("/api/jobs/{job_id}")
def update_job(job_id: int, payload: JobUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Job not found")

    current = dict(row)
    data = payload.dict(exclude_unset=True)

    total = data.get("total_amount", current["total_amount"])
    paid = data.get("paid_amount", current["paid_amount"])
    due = max(0.0, round(total - paid, 2))

    if due == 0 and total > 0:
        payment_status = "Paid"
    elif paid > 0 and due > 0:
        payment_status = "Partial"
    else:
        payment_status = "Unpaid"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    UPDATE jobs SET
        customer_name = ?,
        customer_phone = ?,
        service_category = ?,
        service_details = ?,
        status = ?,
        total_amount = ?,
        paid_amount = ?,
        due_amount = ?,
        payment_mode = ?,
        payment_status = ?,
        notes = ?,
        updated_at = ?
    WHERE id = ?
    """, (
        data.get("customer_name", current["customer_name"]),
        data.get("customer_phone", current["customer_phone"]),
        data.get("service_category", current["service_category"]),
        data.get("service_details", current["service_details"]),
        data.get("status", current["status"]),
        total, paid, due,
        data.get("payment_mode", current["payment_mode"]),
        payment_status,
        data.get("notes", current["notes"]),
        now_str,
        job_id
    ))

    conn.commit()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    updated_job = dict(cursor.fetchone())
    conn.close()

    return updated_job


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Job {job_id} deleted"}


@app.get("/api/stats")
def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    today_prefix = datetime.now().strftime("%Y-%m-%d")

    # Today's jobs
    cursor.execute("SELECT COUNT(*) as count FROM jobs WHERE created_at LIKE ?", (f"{today_prefix}%",))
    today_jobs = cursor.fetchone()["count"]

    # Today's revenue & breakdown
    cursor.execute("""
    SELECT 
        COALESCE(SUM(paid_amount), 0) as total_collection,
        COALESCE(SUM(CASE WHEN payment_mode = 'Cash' THEN paid_amount ELSE 0 END), 0) as cash_collection,
        COALESCE(SUM(CASE WHEN payment_mode = 'UPI' THEN paid_amount ELSE 0 END), 0) as upi_collection
    FROM jobs 
    WHERE created_at LIKE ?
    """, (f"{today_prefix}%",))
    rev_row = cursor.fetchone()

    # Total pending dues (Udhari across all jobs)
    cursor.execute("SELECT COALESCE(SUM(due_amount), 0) as total_due FROM jobs WHERE due_amount > 0")
    total_due = cursor.fetchone()["total_due"]

    # Pending / active work count
    cursor.execute("SELECT COUNT(*) as count FROM jobs WHERE status IN ('Pending', 'In Progress')")
    pending_jobs = cursor.fetchone()["count"]

    conn.close()

    return {
        "today_jobs": today_jobs,
        "today_collection": round(rev_row["total_collection"], 2),
        "today_cash": round(rev_row["cash_collection"], 2),
        "today_upi": round(rev_row["upi_collection"], 2),
        "total_due": round(total_due, 2),
        "active_work_count": pending_jobs
    }


@app.get("/api/customers")
def get_customers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        customer_phone,
        MAX(customer_name) as customer_name,
        COUNT(id) as total_orders,
        SUM(total_amount) as total_billed,
        SUM(paid_amount) as total_paid,
        SUM(due_amount) as total_due,
        MAX(created_at) as last_visit
    FROM jobs
    GROUP BY customer_phone
    ORDER BY total_due DESC, total_orders DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# Static files mount
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Cyber Cafe API Server Running. Please create static/index.html"}


if __name__ == "__main__":
    import uvicorn
    init_db()
    # Runs on all local network interfaces so phone can access via Wi-Fi!
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
