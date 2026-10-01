from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional
from database import get_db
from models import TableCreate

router = APIRouter(prefix="/api/tables", tags=["tables"])

@router.get("/")
def get_tables(search: Optional[str] = Query(None)):
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM Restaurant_Tables WHERE 1=1"
        params = []
        if search:
            query += " AND (table_id LIKE ? OR capacity LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term])
        query += " ORDER BY table_id"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

@router.get("/status")
def get_tables_pos_status():
    """
    Returns tables with real-time status:
    - 'reserved' (Yellow): active reservation in window
    - 'occupied' (Red): has an active bill with items and no payment_time yet
    - 'available' (Green): free to be seated
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Restaurant_Tables ORDER BY table_id")
        tables = [dict(row) for row in cursor.fetchall()]

        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        start_window = (now - timedelta(minutes=20)).strftime("%H:%M:%S")
        end_window = (now + timedelta(minutes=60)).strftime("%H:%M:%S")

        result = []
        for t in tables:
            tid = t["table_id"]
            
            # Check latest bill
            cursor.execute("SELECT bill_id, payment_time FROM Bills WHERE table_id = ? ORDER BY bill_time DESC LIMIT 1", (tid,))
            latest_bill = cursor.fetchone()
            
            latest_bill_id = None
            has_unpaid_items = False
            if latest_bill:
                latest_bill_id = latest_bill["bill_id"]
                is_paid = bool(latest_bill["payment_time"])
                if not is_paid:
                    # check if it has bill items
                    cursor.execute("SELECT COUNT(*) FROM Bill_Items WHERE bill_id = ?", (latest_bill_id,))
                    count = cursor.fetchone()[0]
                    if count > 0:
                        has_unpaid_items = True

            # Check reservations for today near this time
            cursor.execute(
                """
                SELECT * FROM Reservations
                WHERE table_id = ? AND reservation_date = ? 
                AND reservation_time BETWEEN ? AND ?
                LIMIT 1
                """,
                (tid, current_date, start_window, end_window)
            )
            res = cursor.fetchone()
            is_reserved = res is not None

            # Determine color state
            if is_reserved:
                status_code = "reserved"
                color = "#f8de22" # Yellow
            elif has_unpaid_items:
                status_code = "occupied"
                color = "#d80032" # Red
            else:
                status_code = "available"
                color = "#17594a" # Green

            result.append({
                "table_id": tid,
                "capacity": t["capacity"],
                "is_available": t["is_available"],
                "status": status_code,
                "color": color,
                "latest_bill_id": latest_bill_id,
                "reservation_info": dict(res) if res else None
            })

        return result

@router.post("/")
def create_table(req: TableCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT table_id FROM Restaurant_Tables WHERE table_id = ?", (req.table_id,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Table ID already exists")

        cursor.execute(
            "INSERT INTO Restaurant_Tables (table_id, capacity, is_available) VALUES (?, ?, ?)",
            (req.table_id, req.capacity, req.is_available or 1)
        )
        return {"success": True, "message": "Table created successfully", "table_id": req.table_id}

@router.delete("/{table_id}")
def delete_table(table_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Restaurant_Tables WHERE table_id = ?", (table_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Table not found")
        return {"success": True, "message": "Table deleted successfully"}
