from fastapi import APIRouter, HTTPException
from datetime import datetime
from database import get_db

router = APIRouter(prefix="/api/kitchen", tags=["kitchen"])

@router.get("/")
def get_active_orders():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT k.kitchen_id, k.table_id, k.item_id, k.quantity, k.time_submitted, k.time_ended,
                   COALESCE(m.item_name, 'Unknown Item') AS item_name,
                   m.item_category
            FROM Kitchen k
            LEFT JOIN Menu m ON k.item_id = m.item_id
            WHERE k.time_ended IS NULL
            ORDER BY k.time_submitted ASC
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        return rows

@router.post("/done/{kitchen_id}")
def mark_kitchen_order_done(kitchen_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "UPDATE Kitchen SET time_ended = ? WHERE kitchen_id = ?",
            (now_str, kitchen_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Kitchen order not found")
        return {"success": True, "message": "Order marked as done", "kitchen_id": kitchen_id}

@router.post("/undo")
def undo_last_completed_order():
    with get_db() as conn:
        cursor = conn.cursor()
        # Find the most recently ended order
        cursor.execute("""
            SELECT kitchen_id FROM Kitchen
            WHERE time_ended IS NOT NULL
            ORDER BY time_ended DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="No completed kitchen orders to undo.")

        last_id = row["kitchen_id"]
        cursor.execute(
            "UPDATE Kitchen SET time_ended = NULL WHERE kitchen_id = ?",
            (last_id,)
        )
        return {"success": True, "message": "Last completed order restored", "kitchen_id": last_id}
