from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date
from database import get_db
from models import StaffCreate, StaffUpdate, MemberCreate, AccountCreate

router = APIRouter(prefix="/api/manage", tags=["management"])

# ================= STAFF CRUD =================
@router.get("/staff")
def get_all_staff(search: Optional[str] = Query(None)):
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT s.staff_id, s.staff_name, s.role, s.account_id, a.email, a.phone_number
            FROM Staffs s
            LEFT JOIN Accounts a ON s.account_id = a.account_id
            WHERE 1=1
        """
        params = []
        if search:
            query += " AND (s.staff_name LIKE ? OR s.role LIKE ? OR s.staff_id LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])
        query += " ORDER BY s.staff_id"
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

@router.post("/staff")
def create_staff(req: StaffCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        # Verify account exists
        cursor.execute("SELECT account_id FROM Accounts WHERE account_id = ?", (req.account_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Account ID does not exist.")

        cursor.execute(
            "INSERT INTO Staffs (staff_name, role, account_id) VALUES (?, ?, ?)",
            (req.staff_name, req.role, req.account_id)
        )
        return {"success": True, "message": "Staff member created", "staff_id": cursor.lastrowid}

@router.put("/staff/{staff_id}")
def update_staff(staff_id: int, req: StaffUpdate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Staffs SET staff_name = ?, role = ?, account_id = ? WHERE staff_id = ?",
            (req.staff_name, req.role, req.account_id, staff_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Staff member not found")
        return {"success": True, "message": "Staff member updated"}

@router.delete("/staff/{staff_id}")
def delete_staff(staff_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Staffs WHERE staff_id = ?", (staff_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Staff member not found")
        return {"success": True, "message": "Staff member deleted"}

# ================= MEMBERSHIPS CRUD =================
@router.get("/members")
def get_all_members(search: Optional[str] = Query(None)):
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT m.member_id, m.member_name, m.points, m.account_id, a.email, a.phone_number
            FROM Memberships m
            LEFT JOIN Accounts a ON m.account_id = a.account_id
            WHERE 1=1
        """
        params = []
        if search:
            query += " AND (m.member_name LIKE ? OR m.member_id LIKE ? OR a.email LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])
        query += " ORDER BY m.member_id"
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

@router.post("/members")
def create_member(req: MemberCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT account_id FROM Accounts WHERE account_id = ?", (req.account_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Account ID does not exist.")

        cursor.execute(
            "INSERT INTO Memberships (member_name, points, account_id) VALUES (?, ?, ?)",
            (req.member_name, req.points or 0, req.account_id)
        )
        return {"success": True, "message": "Member created", "member_id": cursor.lastrowid}

@router.delete("/members/{member_id}")
def delete_member(member_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Memberships WHERE member_id = ?", (member_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Member not found")
        return {"success": True, "message": "Member deleted"}

# ================= ACCOUNTS CRUD =================
@router.get("/accounts")
def get_all_accounts(search: Optional[str] = Query(None)):
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT account_id, email, register_date, phone_number, password FROM Accounts WHERE 1=1"
        params = []
        if search:
            query += " AND (email LIKE ? OR account_id LIKE ? OR phone_number LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])
        query += " ORDER BY account_id"
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

@router.post("/accounts")
def create_account(req: AccountCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT account_id FROM Accounts WHERE email = ?", (req.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists.")

        today = date.today().strftime("%Y-%m-%d")
        cursor.execute(
            "INSERT INTO Accounts (email, register_date, phone_number, password) VALUES (?, ?, ?, ?)",
            (req.email, today, req.phone_number, req.password)
        )
        return {"success": True, "message": "Account created", "account_id": cursor.lastrowid}

@router.delete("/accounts/{account_id}")
def delete_account(account_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Staffs WHERE account_id = ?", (account_id,))
        cursor.execute("DELETE FROM Memberships WHERE account_id = ?", (account_id,))
        cursor.execute("DELETE FROM Accounts WHERE account_id = ?", (account_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Account not found")
        return {"success": True, "message": "Account deleted"}

# ================= BILLS CRUD =================
@router.get("/bills")
def get_all_bills(search: Optional[str] = Query(None)):
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT b.bill_id, b.staff_id, b.member_id, b.reservation_id, b.table_id,
                   b.card_id, b.payment_method, b.bill_time, b.payment_time,
                   s.staff_name, m.member_name,
                   COUNT(bi.bill_item_id) as items_count,
                   COALESCE(SUM(menu.item_price * bi.quantity), 0) as subtotal
            FROM Bills b
            LEFT JOIN Staffs s ON b.staff_id = s.staff_id
            LEFT JOIN Memberships m ON b.member_id = m.member_id
            LEFT JOIN Bill_Items bi ON b.bill_id = bi.bill_id
            LEFT JOIN Menu menu ON bi.item_id = menu.item_id
            WHERE 1=1
        """
        params = []
        if search:
            query += " AND (b.bill_id LIKE ? OR b.table_id LIKE ? OR s.staff_name LIKE ? OR m.member_name LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term, term])
        query += " GROUP BY b.bill_id ORDER BY b.bill_time DESC"
        cursor.execute(query, params)
        rows = []
        for r in cursor.fetchall():
            sub = r["subtotal"]
            tax = round(sub * 0.10, 2)
            grand = round(sub + tax, 2)
            rows.append({
                "bill_id": r["bill_id"],
                "table_id": r["table_id"],
                "staff_id": r["staff_id"],
                "staff_name": r["staff_name"] or "N/A",
                "member_id": r["member_id"],
                "member_name": r["member_name"] or "Non-member",
                "reservation_id": r["reservation_id"],
                "payment_method": r["payment_method"] or "Unpaid",
                "bill_time": r["bill_time"],
                "payment_time": r["payment_time"],
                "items_count": r["items_count"],
                "subtotal": round(sub, 2),
                "grand_total": grand
            })
        return rows

@router.delete("/bills/{bill_id}")
def delete_bill(bill_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Bill_Items WHERE bill_id = ?", (bill_id,))
        cursor.execute("DELETE FROM Bills WHERE bill_id = ?", (bill_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Bill not found")
        return {"success": True, "message": "Bill and items deleted"}
