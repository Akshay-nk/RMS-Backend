import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_all():
    print("Testing Backend API Endpoints...")

    # 1. Root
    res = client.get("/")
    assert res.status_code == 200, f"Root failed: {res.text}"
    print("[PASS] Root endpoint OK")

    # 2. Customer Auth
    res = client.post("/api/auth/customer/login", json={"email": "zoe@gmail.com", "password": "passworddef"})
    assert res.status_code == 200, f"Customer login failed: {res.text}"
    data = res.json()
    assert data["email"] == "zoe@gmail.com"
    assert "vip_status" in data
    print(f"[PASS] Customer login OK (Member: {data['member_name']}, VIP: {data['vip_status']})")

    # 3. Staff Auth
    res = client.post("/api/auth/staff/login", json={"account_id": 1, "password": "password123"})
    assert res.status_code == 200, f"Staff login failed: {res.text}"
    s_data = res.json()
    assert s_data["staff_id"] == 1
    print(f"[PASS] Staff login OK (Staff: {s_data['staff_name']}, Role: {s_data['role']})")

    # 4. Admin Passcode Verify
    res = client.post("/api/auth/admin-verify", json={"admin_id": "99999", "password": "12345"})
    assert res.status_code == 200
    res_bad = client.post("/api/auth/admin-verify", json={"admin_id": "99999", "password": "wrong"})
    assert res_bad.status_code == 403
    print("[PASS] Admin verification OK")

    # 5. Menu
    res = client.get("/api/menu/")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 90
    print(f"[PASS] Menu items list OK ({len(items)} items found)")

    res_cat = client.get("/api/menu/categories")
    assert res_cat.status_code == 200
    cats = res_cat.json()["categories"]
    assert "Main Dishes" in cats
    print(f"[PASS] Menu categories OK: {cats}")

    # 6. Tables & POS Status
    res = client.get("/api/tables/status")
    assert res.status_code == 200
    t_status = res.json()
    assert len(t_status) == 10
    print(f"[PASS] Tables status OK (Table 1 status: {t_status[0]['status']})")

    # 7. Reservation Availability & Create
    res = client.get("/api/reservations/check-availability?reservation_date=2026-10-15&reservation_time=14:00:00&head_count=2")
    assert res.status_code == 200
    avail = res.json()
    assert len(avail["available_tables"]) > 0
    print(f"[PASS] Reservation availability OK ({len(avail['available_tables'])} tables available)")

    chosen_table = avail["available_tables"][0]["table_id"]
    res_create = client.post("/api/reservations/", json={
        "customer_name": "Antigravity Tester",
        "table_id": chosen_table,
        "reservation_time": "14:00:00",
        "reservation_date": "2026-10-15",
        "head_count": 2,
        "special_request": "Window seat please"
    })
    assert res_create.status_code == 200
    res_id = res_create.json()["reservation_id"]
    print(f"[PASS] Reservation created OK (ID: {res_id})")

    # 8. POS Ordering & Billing Flow
    test_table = 9
    client.post(f"/api/pos/new-customer/{test_table}")
    bill_info = client.get(f"/api/pos/table-bill/{test_table}").json()
    test_bill_id = bill_info["bill_id"]
    print(f"[PASS] Created active POS bill {test_bill_id} for Table {test_table}")

    # Add item MD1 (Prime Rib Steak) to cart
    res_cart = client.post("/api/pos/cart/add", json={
        "table_id": test_table,
        "item_id": "MD1",
        "quantity": 2,
        "bill_id": test_bill_id
    })
    assert res_cart.status_code == 200
    print("[PASS] Added item to cart")

    # Check Kitchen queue
    k_orders = client.get("/api/kitchen/").json()
    assert any(k["table_id"] == test_table and k["item_id"] == "MD1" for k in k_orders)
    print("[PASS] Verified item appeared in Kitchen orders queue")

    # Mark Kitchen item done and undo
    k_target = next(k for k in k_orders if k["table_id"] == test_table and k["item_id"] == "MD1")
    res_k_done = client.post(f"/api/kitchen/done/{k_target['kitchen_id']}")
    assert res_k_done.status_code == 200
    res_k_undo = client.post("/api/kitchen/undo")
    assert res_k_undo.status_code == 200
    print("[PASS] Kitchen Done & Undo cycle OK")

    # Check bill total
    bill_updated = client.get(f"/api/pos/table-bill/{test_table}").json()
    assert bill_updated["subtotal"] == 192.0 # 96 * 2
    assert bill_updated["tax"] == 19.2 # 10%
    assert bill_updated["grand_total"] == 211.2
    print(f"[PASS] POS Cart calculations OK: Subtotal={bill_updated['subtotal']}, Grand Total={bill_updated['grand_total']}")

    # Pay bill with Cash
    res_pay = client.post("/api/pos/pay/cash", json={
        "bill_id": test_bill_id,
        "staff_id": 1,
        "member_id": 1,
        "reservation_id": None,
        "payment_amount": 250.0
    })
    assert res_pay.status_code == 200
    pay_data = res_pay.json()
    assert pay_data["change"] == round(250.0 - 211.2, 2)
    print(f"[PASS] Cash payment successful! Change: RM {pay_data['change']}")

    # Receipt
    receipt = client.get(f"/api/pos/receipt/{test_bill_id}").json()
    assert receipt["grand_total"] == 211.2
    assert len(receipt["items"]) == 1
    print(f"[PASS] POS Receipt generated OK (Bill #{receipt['bill_id']})")

    # 9. Reports & Statistics
    stats = client.get("/api/reports/statistics").json()
    assert "total_revenue" in stats
    assert stats["total_revenue"] > 0
    print(f"[PASS] Revenue statistics OK (Total revenue all time: RM {stats['total_revenue']})")

    sales = client.get("/api/reports/sales?sort_order=desc").json()
    assert len(sales["items"]) > 0
    print(f"[PASS] Sales report OK (Top item: {sales['items'][0]['item_name']})")

    # 10. Management CRUD
    staff_list = client.get("/api/manage/staff").json()
    assert len(staff_list) >= 10
    print(f"[PASS] Management staff listing OK ({len(staff_list)} staff)")

    print("\n==========================================")
    print("SUCCESS: ALL BACKEND TESTS PASSED WITH 0 ERRORS!")
    print("==========================================")

if __name__ == "__main__":
    test_all()
