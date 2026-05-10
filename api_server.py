"""
api_server.py – Byblos CRM v2 REST API Server (FastAPI)
=========================================================
Vollwertige REST-API für Drittsystem-Integration.

Installation: pip install fastapi uvicorn
Start:        uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
Docs:         http://localhost:8000/docs
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List

try:
    from fastapi import FastAPI, HTTPException, Depends, Header, Query
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    FASTAPI_OK = True
except ImportError:
    FASTAPI_OK = False
    print("⚠️  FastAPI nicht installiert. Bitte: pip install fastapi uvicorn")
    raise SystemExit(1)


# ─────────────────────────────────────────────────────────────
# Konfiguration
# ─────────────────────────────────────────────────────────────

DB_PATH = Path(__file__).parent / "byblos_crm.db"

app = FastAPI(
    title="Byblos CRM REST-API",
    version="2.0",
    description="Vollwertige REST-API für Byblos Sicherheitsdienst & Service",
    contact={"name": "Byblos Support"},
)

# CORS für Web-Apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Produktion einschränken
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# DB-Verbindung
# ─────────────────────────────────────────────────────────────

def get_db():
    if not DB_PATH.exists():
        raise HTTPException(503, f"Datenbank nicht gefunden: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def verify_api_key(x_api_key: Optional[str] = Header(None), conn=Depends(get_db)):
    if not x_api_key:
        raise HTTPException(401, "X-API-Key Header erforderlich")
    cur = conn.execute(
        "SELECT key_name, permissions FROM api_keys WHERE api_key=? AND active=1",
        (x_api_key,)
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(403, "Ungültiger oder deaktivierter API-Key")
    # Last-used aktualisieren
    conn.execute("UPDATE api_keys SET last_used=? WHERE api_key=?",
                 (datetime.now().isoformat(), x_api_key))
    conn.commit()
    return dict(row)


# ─────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    company: str
    contact_person: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    street: Optional[str] = ""
    zip_city: Optional[str] = ""


class CheckinRequest(BaseModel):
    employee_id: int
    shift_id: Optional[int] = None
    checkin_type: str = "start"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = ""
    notes: Optional[str] = ""


# ─────────────────────────────────────────────────────────────
# Public Endpoints (kein Key)
# ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "service": "Byblos CRM v2 REST-API",
        "version": "2.0",
        "documentation": "/docs",
        "status": "online",
    }


@app.get("/api/v1/health", tags=["Info"])
def health_check():
    db_ok = DB_PATH.exists()
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "Byblos CRM v2",
        "database": "connected" if db_ok else "missing",
        "timestamp": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# Customers
# ─────────────────────────────────────────────────────────────

@app.get("/api/v1/customers", tags=["Customers"], dependencies=[Depends(verify_api_key)])
def list_customers(
    limit: int = Query(100, le=1000),
    search: Optional[str] = None,
    conn=Depends(get_db),
):
    if search:
        cur = conn.execute(
            "SELECT * FROM customers WHERE company LIKE ? OR email LIKE ? ORDER BY company LIMIT ?",
            (f"%{search}%", f"%{search}%", limit)
        )
    else:
        cur = conn.execute("SELECT * FROM customers ORDER BY company LIMIT ?", (limit,))
    return [dict(row) for row in cur.fetchall()]


@app.get("/api/v1/customers/{customer_id}", tags=["Customers"],
         dependencies=[Depends(verify_api_key)])
def get_customer(customer_id: int, conn=Depends(get_db)):
    cur = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Kunde nicht gefunden")
    return dict(row)


@app.post("/api/v1/customers", tags=["Customers"], status_code=201,
          dependencies=[Depends(verify_api_key)])
def create_customer(customer: CustomerCreate, conn=Depends(get_db)):
    # Auto-Nummer
    cur = conn.execute("SELECT MAX(CAST(SUBSTR(customer_no, 4) AS INT)) as max_no FROM customers WHERE customer_no LIKE 'SD-%'")
    row = cur.fetchone()
    next_no = (row["max_no"] or 0) + 1
    cust_no = f"SD-{next_no:04d}"
    conn.execute(
        """INSERT INTO customers(customer_no,company,contact_person,email,phone,street,zip_city)
           VALUES(?,?,?,?,?,?,?)""",
        (cust_no, customer.company, customer.contact_person, customer.email,
         customer.phone, customer.street, customer.zip_city)
    )
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
    return {"id": new_id, "customer_no": cust_no, **customer.dict()}


# ─────────────────────────────────────────────────────────────
# Invoices
# ─────────────────────────────────────────────────────────────

@app.get("/api/v1/invoices", tags=["Invoices"], dependencies=[Depends(verify_api_key)])
def list_invoices(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    limit: int = Query(100, le=1000),
    conn=Depends(get_db),
):
    where, params = [], []
    if status:
        where.append("status=?"); params.append(status)
    if customer_id:
        where.append("customer_id=?"); params.append(customer_id)

    sql = "SELECT * FROM invoices"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY invoice_date DESC LIMIT ?"
    params.append(limit)

    cur = conn.execute(sql, tuple(params))
    return [dict(row) for row in cur.fetchall()]


@app.get("/api/v1/invoices/{invoice_id}", tags=["Invoices"],
         dependencies=[Depends(verify_api_key)])
def get_invoice(invoice_id: int, conn=Depends(get_db)):
    cur = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Rechnung nicht gefunden")
    inv = dict(row)
    items = conn.execute(
        "SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY position",
        (invoice_id,)
    ).fetchall()
    inv["items"] = [dict(i) for i in items]
    return inv


@app.get("/api/v1/invoices/{invoice_id}/pdf", tags=["Invoices"],
         dependencies=[Depends(verify_api_key)])
def get_invoice_pdf(invoice_id: int, conn=Depends(get_db)):
    cur = conn.execute("SELECT pdf_path, invoice_no FROM invoices WHERE id=?", (invoice_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404)
    if not row["pdf_path"]:
        raise HTTPException(404, "PDF noch nicht erzeugt – im CRM erstellen lassen")
    pdf_path = Path(row["pdf_path"])
    if not pdf_path.exists():
        raise HTTPException(404, "PDF-Datei nicht gefunden")
    return FileResponse(str(pdf_path), media_type="application/pdf",
                         filename=f"{row['invoice_no']}.pdf")


# ─────────────────────────────────────────────────────────────
# Employees & Shifts
# ─────────────────────────────────────────────────────────────

@app.get("/api/v1/employees", tags=["Employees"], dependencies=[Depends(verify_api_key)])
def list_employees(active_only: bool = True, conn=Depends(get_db)):
    sql = "SELECT id, employee_no, name, email, phone, active FROM employees"
    if active_only:
        sql += " WHERE active=1"
    sql += " ORDER BY name"
    cur = conn.execute(sql)
    return [dict(row) for row in cur.fetchall()]


@app.get("/api/v1/shifts", tags=["Shifts"], dependencies=[Depends(verify_api_key)])
def list_shifts(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    employee_id: Optional[int] = None,
    conn=Depends(get_db),
):
    where = []
    params = []
    if date_from:
        where.append("shift_date >= ?"); params.append(date_from)
    if date_to:
        where.append("shift_date <= ?"); params.append(date_to)
    if employee_id:
        where.append("employee_id = ?"); params.append(employee_id)

    sql = "SELECT * FROM shifts"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY shift_date, start_time"

    cur = conn.execute(sql, tuple(params))
    return [dict(row) for row in cur.fetchall()]


@app.post("/api/v1/checkin", tags=["Shifts"], status_code=201,
          dependencies=[Depends(verify_api_key)])
def gps_checkin(checkin: CheckinRequest, conn=Depends(get_db)):
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO gps_checkins(employee_id,shift_id,checkin_type,checkin_time,
           latitude,longitude,address,notes)
           VALUES(?,?,?,?,?,?,?,?)""",
        (checkin.employee_id, checkin.shift_id, checkin.checkin_type, now,
         checkin.latitude, checkin.longitude, checkin.address, checkin.notes)
    )
    conn.commit()
    return {"status": "registered", "time": now}


# ─────────────────────────────────────────────────────────────
# KPIs & Reports
# ─────────────────────────────────────────────────────────────

@app.get("/api/v1/kpis", tags=["Reports"], dependencies=[Depends(verify_api_key)])
def get_kpis(days: int = 30, conn=Depends(get_db)):
    cur = conn.execute(
        "SELECT * FROM daily_kpis ORDER BY kpi_date DESC LIMIT ?",
        (days,)
    )
    return [dict(row) for row in cur.fetchall()]


@app.get("/api/v1/dashboard", tags=["Reports"], dependencies=[Depends(verify_api_key)])
def dashboard_summary(conn=Depends(get_db)):
    """Zusammenfassende Dashboard-Daten."""
    today_str = datetime.now().date().isoformat()
    month_str = today_str[:7]

    summary = {
        "customers_total": conn.execute("SELECT COUNT(*) as n FROM customers").fetchone()["n"],
        "employees_active": conn.execute("SELECT COUNT(*) as n FROM employees WHERE active=1").fetchone()["n"],
        "invoices_open": conn.execute("SELECT COUNT(*) as n FROM invoices WHERE status='offen'").fetchone()["n"],
        "invoices_overdue": conn.execute("SELECT COUNT(*) as n FROM invoices WHERE status='ueberfaellig'").fetchone()["n"],
        "revenue_this_month": conn.execute(
            "SELECT COALESCE(SUM(gross_total),0) as v FROM invoices WHERE substr(invoice_date,1,7)=? AND status='bezahlt'",
            (month_str,)
        ).fetchone()["v"],
        "expenses_this_month": conn.execute(
            "SELECT COALESCE(SUM(gross_amount),0) as v FROM expenses WHERE bwa_month=?",
            (month_str,)
        ).fetchone()["v"],
        "shifts_today": conn.execute(
            "SELECT COUNT(*) as n FROM shifts WHERE shift_date=?",
            (today_str,)
        ).fetchone()["n"],
        "shifts_unassigned_today": conn.execute(
            "SELECT COUNT(*) as n FROM shifts WHERE shift_date=? AND employee_id IS NULL",
            (today_str,)
        ).fetchone()["n"],
        "timestamp": datetime.now().isoformat(),
    }
    summary["result_this_month"] = summary["revenue_this_month"] - summary["expenses_this_month"]
    return summary


# ─────────────────────────────────────────────────────────────
# Webhook-Empfänger (für externe Events)
# ─────────────────────────────────────────────────────────────

@app.post("/api/v1/webhook", tags=["Webhooks"])
def receive_webhook(payload: dict, conn=Depends(get_db)):
    """
    Generischer Webhook-Empfänger für externe Events.
    Beispiele: Stripe-Payment, Zapier-Trigger, IoT-Sensoren.
    """
    conn.execute(
        """INSERT INTO automation_log(action,result) VALUES(?,?)""",
        ("webhook_received", str(payload)[:500])
    )
    conn.commit()
    return {"status": "received", "timestamp": datetime.now().isoformat()}


# ─────────────────────────────────────────────────────────────
# Statistiken & Suche
# ─────────────────────────────────────────────────────────────

@app.get("/api/v1/search", tags=["Search"], dependencies=[Depends(verify_api_key)])
def global_search(q: str = Query(..., min_length=2), conn=Depends(get_db)):
    """Cross-Table Suche."""
    q_like = f"%{q}%"
    results = {
        "customers": [dict(r) for r in conn.execute(
            "SELECT id, customer_no, company, email FROM customers WHERE company LIKE ? OR email LIKE ? LIMIT 10",
            (q_like, q_like)
        ).fetchall()],
        "invoices": [dict(r) for r in conn.execute(
            "SELECT id, invoice_no, invoice_date, gross_total FROM invoices WHERE invoice_no LIKE ? OR description LIKE ? LIMIT 10",
            (q_like, q_like)
        ).fetchall()],
        "employees": [dict(r) for r in conn.execute(
            "SELECT id, employee_no, name FROM employees WHERE name LIKE ? LIMIT 10",
            (q_like,)
        ).fetchall()],
    }
    results["total_hits"] = sum(len(v) for v in results.values() if isinstance(v, list))
    return results


if __name__ == "__main__":
    import uvicorn
    print("🚀 Byblos CRM API-Server startet auf http://0.0.0.0:8000")
    print("📖 API-Dokumentation: http://localhost:8000/docs")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
