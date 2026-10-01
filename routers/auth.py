from fastapi import APIRouter, HTTPException, status
from datetime import date
from database import get_db
from models import (
    CustomerRegisterRequest,
    CustomerLoginRequest,
    StaffLoginRequest,
    AdminVerifyRequest,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/customer/register")
def customer_register(req: CustomerRegisterRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        # Check if email exists
        cursor.execute("SELECT account_id FROM Accounts WHERE email = ?", (req.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email is already registered.")

        # Insert account
        today = date.today().strftime("%Y-%m-%d")
        cursor.execute(
            "INSERT INTO Accounts (email, register_date, phone_number, password) VALUES (?, ?, ?, ?)",
            (req.email, today, req.phone_number, req.password)
        )
        account_id = cursor.lastrowid

        # Insert membership
        cursor.execute(
            "INSERT INTO Memberships (member_name, points, account_id) VALUES (?, ?, ?)",
            (req.member_name, 0, account_id)
        )
        member_id = cursor.lastrowid

        return {
            "success": True,
            "message": "Registration successful!",
            "account_id": account_id,
            "member_id": member_id,
            "member_name": req.member_name,
            "email": req.email,
        }

@router.post("/customer/login")
def customer_login(req: CustomerLoginRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Accounts WHERE email = ?", (req.email,))
        acc = cursor.fetchone()
        if not acc:
            raise HTTPException(status_code=401, detail="No account found with this email.")

        if acc["password"] != req.password:
            raise HTTPException(status_code=401, detail="Invalid password. Please try again.")

        # Get membership details
        cursor.execute("SELECT * FROM Memberships WHERE account_id = ?", (acc["account_id"],))
        member = cursor.fetchone()

        points = member["points"] if member else 0
        member_name = member["member_name"] if member else "Member"
        member_id = member["member_id"] if member else None
        vip_status = "VIP" if points >= 1000 else "Regular"
        points_to_vip = max(0, 1000 - points)

        return {
            "success": True,
            "account_id": acc["account_id"],
            "member_id": member_id,
            "member_name": member_name,
            "email": acc["email"],
            "phone_number": acc["phone_number"],
            "register_date": acc["register_date"],
            "points": points,
            "vip_status": vip_status,
            "points_to_vip": points_to_vip,
        }

@router.get("/customer/profile/{account_id}")
def customer_profile(account_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.member_id, m.member_name, m.points, a.account_id, a.email, a.phone_number, a.register_date
            FROM Memberships AS m
            INNER JOIN Accounts AS a ON m.account_id = a.account_id
            WHERE m.account_id = ?
        """, (account_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Member profile not found.")

        points = row["points"]
        vip_status = "VIP" if points >= 1000 else "Regular"
        return {
            "account_id": row["account_id"],
            "member_id": row["member_id"],
            "member_name": row["member_name"],
            "email": row["email"],
            "phone_number": row["phone_number"],
            "register_date": row["register_date"],
            "points": points,
            "vip_status": vip_status,
            "points_to_vip": max(0, 1000 - points),
        }

@router.post("/staff/login")
def staff_login(req: StaffLoginRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Accounts WHERE account_id = ?", (req.account_id,))
        acc = cursor.fetchone()
        if not acc:
            raise HTTPException(status_code=401, detail="Staff ID (Account ID) not found.")

        if acc["password"] != req.password:
            raise HTTPException(status_code=401, detail="Incorrect password. Please try again.")

        # Check Staff record
        cursor.execute("SELECT * FROM Staffs WHERE account_id = ?", (req.account_id,))
        staff = cursor.fetchone()
        if not staff:
            raise HTTPException(status_code=403, detail="Account is not assigned to a staff role.")

        return {
            "success": True,
            "account_id": acc["account_id"],
            "staff_id": staff["staff_id"],
            "staff_name": staff["staff_name"],
            "role": staff["role"],
        }

@router.post("/admin-verify")
def verify_admin(req: AdminVerifyRequest):
    combined = f"{req.admin_id.strip()}{req.password.strip()}"
    if combined == "9999912345":
        return {"success": True, "message": "Admin credentials verified."}
    raise HTTPException(status_code=403, detail="Incorrect Admin ID or Password!")
