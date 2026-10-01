from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional
from database import get_db
from models import (
    AddToCartRequest,
    DeleteCartItemRequest,
    CashPaymentRequest,
    CardPaymentRequest
)

router = APIRouter(prefix="/api/pos", tags=["pos"])

TAX_RATE = 0.10 # 10% tax

@router.get("/table-bill/{table_id}")
def get_or_create_table_bill(table_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify table exists
        cursor.execute("SELECT * FROM Restaurant_Tables WHERE table_id = ?", (table_id,))
        table = cursor.fetchone()
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")

        # Find latest bill for this table
        cursor.execute(
            "SELECT * FROM Bills WHERE table_id = ? ORDER BY bill_time DESC LIMIT 1",
            (table_id,)
        )
        bill = cursor.fetchone()

        # If no bill exists or the latest bill is already paid, create a new active bill
        if not bill or bill["payment_time"] is not None:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO Bills (table_id, bill_time) VALUES (?, ?)",
                (table_id, now_str)
            )
            bill_id = cursor.lastrowid
            cursor.execute("SELECT * FROM Bills WHERE bill_id = ?", (bill_id,))
            bill = cursor.fetchone()

        bill_id = bill["bill_id"]
        is_paid = bill["payment_time"] is not None

        # Fetch cart items
        cursor.execute("""
            SELECT bi.bill_item_id, bi.bill_id, bi.item_id, bi.quantity,
                   m.item_name, m.item_price, m.item_category, m.item_type
            FROM Bill_Items bi
            JOIN Menu m ON bi.item_id = m.item_id
            WHERE bi.bill_id = ?
            ORDER BY bi.bill_item_id
        """, (bill_id,))
        items = []
        subtotal = 0.0
        for row in cursor.fetchall():
            total_price = row["item_price"] * row["quantity"]
            subtotal += total_price
            items.append({
                "bill_item_id": row["bill_item_id"],
                "item_id": row["item_id"],
                "item_name": row["item_name"],
                "item_category": row["item_category"],
                "item_type": row["item_type"],
                "item_price": row["item_price"],
                "quantity": row["quantity"],
                "total_price": round(total_price, 2)
            })

        tax_amount = round(subtotal * TAX_RATE, 2)
        grand_total = round(subtotal + tax_amount, 2)

        return {
            "bill_id": bill_id,
            "table_id": table_id,
            "bill_time": bill["bill_time"],
            "payment_time": bill["payment_time"],
            "payment_method": bill["payment_method"],
            "is_paid": is_paid,
            "items": items,
            "subtotal": round(subtotal, 2),
            "tax": tax_amount,
            "grand_total": grand_total
        }

@router.post("/new-customer/{table_id}")
def new_customer_session(table_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO Bills (table_id, bill_time) VALUES (?, ?)",
            (table_id, now_str)
        )
        new_bill_id = cursor.lastrowid
        return {"success": True, "message": "New customer session created", "bill_id": new_bill_id}

@router.post("/cart/add")
def add_to_cart(req: AddToCartRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        bill_id = req.bill_id
        if not bill_id:
            # Look up active bill or create one
            cursor.execute(
                "SELECT bill_id, payment_time FROM Bills WHERE table_id = ? ORDER BY bill_time DESC LIMIT 1",
                (req.table_id,)
            )
            b = cursor.fetchone()
            if not b or b["payment_time"] is not None:
                cursor.execute("INSERT INTO Bills (table_id, bill_time) VALUES (?, ?)", (req.table_id, now_str))
                bill_id = cursor.lastrowid
            else:
                bill_id = b["bill_id"]

        # Check if already paid
        cursor.execute("SELECT payment_time FROM Bills WHERE bill_id = ?", (bill_id,))
        b_check = cursor.fetchone()
        if b_check and b_check["payment_time"]:
            raise HTTPException(status_code=400, detail="Bill has already been paid.")

        # Check if item exists in bill_items
        cursor.execute(
            "SELECT * FROM Bill_Items WHERE bill_id = ? AND item_id = ?",
            (bill_id, req.item_id)
        )
        existing = cursor.fetchone()
        if existing:
            new_qty = existing["quantity"] + req.quantity
            cursor.execute(
                "UPDATE Bill_Items SET quantity = ? WHERE bill_item_id = ?",
                (new_qty, existing["bill_item_id"])
            )
        else:
            cursor.execute(
                "INSERT INTO Bill_Items (bill_id, item_id, quantity) VALUES (?, ?, ?)",
                (bill_id, req.item_id, req.quantity)
            )

        # Update or Insert Kitchen queue
        cursor.execute(
            "SELECT kitchen_id, quantity FROM Kitchen WHERE table_id = ? AND item_id = ? AND time_ended IS NULL",
            (req.table_id, req.item_id)
        )
        k_existing = cursor.fetchone()
        if k_existing:
            cursor.execute(
                "UPDATE Kitchen SET quantity = quantity + ?, time_submitted = ? WHERE kitchen_id = ?",
                (req.quantity, now_str, k_existing["kitchen_id"])
            )
        else:
            cursor.execute(
                "INSERT INTO Kitchen (table_id, item_id, quantity, time_submitted) VALUES (?, ?, ?, ?)",
                (req.table_id, req.item_id, req.quantity, now_str)
            )

        return {"success": True, "message": "Item added to cart and kitchen", "bill_id": bill_id}

@router.post("/cart/delete")
def delete_cart_item(req: DeleteCartItemRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        # Verify bill not paid
        cursor.execute("SELECT payment_time FROM Bills WHERE bill_id = ?", (req.bill_id,))
        b = cursor.fetchone()
        if b and b["payment_time"]:
            raise HTTPException(status_code=400, detail="Cannot modify paid bill.")

        cursor.execute("DELETE FROM Bill_Items WHERE bill_item_id = ?", (req.bill_item_id,))
        # Also remove unstarted kitchen order for this item on this table if exists
        cursor.execute(
            "DELETE FROM Kitchen WHERE table_id = ? AND item_id = ? AND time_ended IS NULL",
            (req.table_id, req.item_id)
        )
        return {"success": True, "message": "Item removed from cart"}

@router.get("/validate-checkout")
def validate_checkout(
    staff_id: int = Query(...),
    member_id: Optional[int] = Query(None),
    reservation_id: Optional[int] = Query(None)
):
    with get_db() as conn:
        cursor = conn.cursor()
        # Validate staff
        cursor.execute("SELECT staff_id, staff_name FROM Staffs WHERE staff_id = ?", (staff_id,))
        staff = cursor.fetchone()
        if not staff:
            return {"valid": False, "message": "Staff ID is invalid."}

        member_name = None
        if member_id and member_id != 1:
            cursor.execute("SELECT member_id, member_name FROM Memberships WHERE member_id = ?", (member_id,))
            member = cursor.fetchone()
            if not member:
                return {"valid": False, "message": "Member ID is invalid."}
            member_name = member["member_name"]

        if reservation_id and reservation_id != 1111111:
            cursor.execute("SELECT reservation_id FROM Reservations WHERE reservation_id = ?", (reservation_id,))
            res = cursor.fetchone()
            if not res:
                return {"valid": False, "message": "Reservation ID is invalid."}

        return {
            "valid": True,
            "message": "Staff, member, and reservation verified.",
            "staff_name": staff["staff_name"],
            "member_name": member_name
        }

@router.post("/pay/cash")
def pay_cash(req: CashPaymentRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify bill exists and unpaid
        cursor.execute("SELECT * FROM Bills WHERE bill_id = ?", (req.bill_id,))
        bill = cursor.fetchone()
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        if bill["payment_time"]:
            raise HTTPException(status_code=400, detail="Bill has already been paid.")

        # Calculate grand total
        cursor.execute("""
            SELECT SUM(m.item_price * bi.quantity) AS subtotal
            FROM Bill_Items bi
            JOIN Menu m ON bi.item_id = m.item_id
            WHERE bi.bill_id = ?
        """, (req.bill_id,))
        subtotal = cursor.fetchone()["subtotal"] or 0.0
        grand_total = round(subtotal + (subtotal * TAX_RATE), 2)

        if req.payment_amount < grand_total:
            raise HTTPException(
                status_code=400,
                detail=f"Payment amount (RM {req.payment_amount:.2f}) is less than grand total (RM {grand_total:.2f})."
            )

        change = round(req.payment_amount - grand_total, 2)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Update bill
        cursor.execute(
            """
            UPDATE Bills
            SET payment_method = 'Cash', payment_time = ?, staff_id = ?, member_id = ?, reservation_id = ?
            WHERE bill_id = ?
            """,
            (now_str, req.staff_id, req.member_id or 1, req.reservation_id, req.bill_id)
        )

        # Award member points
        points_earned = int(grand_total)
        if req.member_id and req.member_id != 1:
            cursor.execute(
                "UPDATE Memberships SET points = points + ? WHERE member_id = ?",
                (points_earned, req.member_id)
            )

        return {
            "success": True,
            "message": "Payment successful!",
            "bill_id": req.bill_id,
            "grand_total": grand_total,
            "payment_amount": req.payment_amount,
            "change": change,
            "points_earned": points_earned,
            "payment_time": now_str
        }

@router.post("/pay/card")
def pay_card(req: CardPaymentRequest):
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify bill exists and unpaid
        cursor.execute("SELECT * FROM Bills WHERE bill_id = ?", (req.bill_id,))
        bill = cursor.fetchone()
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        if bill["payment_time"]:
            raise HTTPException(status_code=400, detail="Bill has already been paid.")

        # Calculate grand total
        cursor.execute("""
            SELECT SUM(m.item_price * bi.quantity) AS subtotal
            FROM Bill_Items bi
            JOIN Menu m ON bi.item_id = m.item_id
            WHERE bi.bill_id = ?
        """, (req.bill_id,))
        subtotal = cursor.fetchone()["subtotal"] or 0.0
        grand_total = round(subtotal + (subtotal * TAX_RATE), 2)

        # Store card record
        cursor.execute(
            """
            INSERT INTO card_payments (account_holder_name, card_number, expiry_date, security_code)
            VALUES (?, ?, ?, ?)
            """,
            (req.account_holder_name, req.card_number, req.expiry_date, req.security_code)
        )
        card_id = cursor.lastrowid
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Update bill
        cursor.execute(
            """
            UPDATE Bills
            SET payment_method = 'Card', card_id = ?, payment_time = ?, staff_id = ?, member_id = ?, reservation_id = ?
            WHERE bill_id = ?
            """,
            (card_id, now_str, req.staff_id, req.member_id or 1, req.reservation_id, req.bill_id)
        )

        # Award member points
        points_earned = int(grand_total)
        if req.member_id and req.member_id != 1:
            cursor.execute(
                "UPDATE Memberships SET points = points + ? WHERE member_id = ?",
                (points_earned, req.member_id)
            )

        return {
            "success": True,
            "message": "Card payment processed successfully!",
            "bill_id": req.bill_id,
            "grand_total": grand_total,
            "card_id": card_id,
            "points_earned": points_earned,
            "payment_time": now_str
        }

@router.get("/receipt/{bill_id}")
def get_receipt(bill_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.*, s.staff_name, m.member_name, m.points
            FROM Bills b
            LEFT JOIN Staffs s ON b.staff_id = s.staff_id
            LEFT JOIN Memberships m ON b.member_id = m.member_id
            WHERE b.bill_id = ?
        """, (bill_id,))
        bill = cursor.fetchone()
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")

        cursor.execute("""
            SELECT bi.quantity, m.item_name, m.item_price, (bi.quantity * m.item_price) as item_total
            FROM Bill_Items bi
            JOIN Menu m ON bi.item_id = m.item_id
            WHERE bi.bill_id = ?
        """, (bill_id,))
        items = [dict(row) for row in cursor.fetchall()]

        subtotal = sum(item["item_total"] for item in items)
        tax = round(subtotal * TAX_RATE, 2)
        grand_total = round(subtotal + tax, 2)

        return {
            "bill_id": bill["bill_id"],
            "table_id": bill["table_id"],
            "staff_id": bill["staff_id"],
            "staff_name": bill["staff_name"] or "Staff",
            "member_id": bill["member_id"],
            "member_name": bill["member_name"],
            "reservation_id": bill["reservation_id"],
            "payment_method": bill["payment_method"] or "Cash",
            "bill_time": bill["bill_time"],
            "payment_time": bill["payment_time"],
            "items": items,
            "subtotal": round(subtotal, 2),
            "tax": tax,
            "grand_total": grand_total,
            "points_earned": int(grand_total)
        }
