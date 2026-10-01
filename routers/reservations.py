from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional, List
from database import get_db
from models import ReservationCreate

router = APIRouter(prefix="/api/reservations", tags=["reservations"])

@router.get("/")
def get_reservations(search: Optional[str] = Query(None)):
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM Reservations WHERE 1=1"
        params = []
        if search:
            query += " AND (reservation_id LIKE ? OR customer_name LIKE ? OR reservation_date LIKE ? OR table_id LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term, term])
        query += " ORDER BY reservation_date DESC, reservation_time DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

@router.get("/check-availability")
def check_availability(
    reservation_date: str = Query(...),
    reservation_time: str = Query(...),
    head_count: int = Query(1)
):
    with get_db() as conn:
        cursor = conn.cursor()
        # Find reserved table IDs at this date and time
        cursor.execute(
            "SELECT table_id FROM Reservations WHERE reservation_date = ? AND reservation_time = ?",
            (reservation_date, reservation_time)
        )
        reserved_tables = [row["table_id"] for row in cursor.fetchall()]

        # Query available tables with capacity >= head_count
        if reserved_tables:
            placeholders = ",".join("?" for _ in reserved_tables)
            sql = f"SELECT * FROM Restaurant_Tables WHERE capacity >= ? AND table_id NOT IN ({placeholders}) ORDER BY capacity, table_id"
            cursor.execute(sql, [head_count] + reserved_tables)
        else:
            sql = "SELECT * FROM Restaurant_Tables WHERE capacity >= ? ORDER BY capacity, table_id"
            cursor.execute(sql, (head_count,))

        available_tables = [dict(row) for row in cursor.fetchall()]

        # Also provide pre-generated time slots (10:00 to 20:00 hourly)
        time_slots = [f"{hour:02d}:00:00" for hour in range(10, 21)]

        return {
            "date": reservation_date,
            "time": reservation_time,
            "head_count": head_count,
            "available_tables": available_tables,
            "reserved_table_ids": reserved_tables,
            "time_slots": time_slots
        }

@router.post("/")
def create_reservation(req: ReservationCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        # Verify table exists and has capacity
        cursor.execute("SELECT capacity FROM Restaurant_Tables WHERE table_id = ?", (req.table_id,))
        t = cursor.fetchone()
        if not t:
            raise HTTPException(status_code=404, detail="Selected table does not exist.")

        # Check if already booked
        cursor.execute(
            "SELECT reservation_id FROM Reservations WHERE table_id = ? AND reservation_date = ? AND reservation_time = ?",
            (req.table_id, req.reservation_date, req.reservation_time)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="This table is already reserved for the selected time.")

        # Generate reservation ID (retaining original logic: time/date numbers + table_id or timestamp integer)
        time_part = "".join(filter(str.isdigit, req.reservation_time))[:4]
        date_part = "".join(filter(str.isdigit, req.reservation_date))[-4:]
        reservation_id = int(f"{time_part}{date_part}{req.table_id}")

        # Ensure uniqueness
        cursor.execute("SELECT reservation_id FROM Reservations WHERE reservation_id = ?", (reservation_id,))
        if cursor.fetchone():
            reservation_id = int(datetime.now().strftime("%y%m%d%H%M") + str(req.table_id))

        cursor.execute(
            """
            INSERT INTO Reservations (reservation_id, customer_name, table_id, reservation_time, reservation_date, head_count, special_request)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (reservation_id, req.customer_name, req.table_id, req.reservation_time, req.reservation_date, req.head_count, req.special_request)
        )

        cursor.execute(
            """
            INSERT INTO Table_Availability (availability_id, table_id, reservation_date, reservation_time, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (reservation_id, req.table_id, req.reservation_date, req.reservation_time, "no")
        )

        return {
            "success": True,
            "message": "Reservation created successfully",
            "reservation_id": reservation_id,
            "reservation": {
                "reservation_id": reservation_id,
                "customer_name": req.customer_name,
                "table_id": req.table_id,
                "reservation_time": req.reservation_time,
                "reservation_date": req.reservation_date,
                "head_count": req.head_count,
                "special_request": req.special_request
            }
        }

@router.get("/{reservation_id}")
def get_reservation_receipt(reservation_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Reservations WHERE reservation_id = ?", (reservation_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Reservation not found")
        return dict(row)

@router.delete("/{reservation_id}")
def delete_reservation(reservation_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Reservations WHERE reservation_id = ?", (reservation_id,))
        cursor.execute("DELETE FROM Table_Availability WHERE availability_id = ?", (reservation_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Reservation not found")
        return {"success": True, "message": "Reservation deleted successfully"}
