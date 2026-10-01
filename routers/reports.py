from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional
from database import get_db

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/statistics")
def get_revenue_statistics():
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_month_start = now.strftime("%Y-%m-01")

        # Monday of current week
        weekday = now.weekday() # 0 = Monday
        monday = now - timedelta(days=weekday)
        current_week_start = monday.strftime("%Y-%m-%d")

        # Total revenue all time
        cursor.execute("""
            SELECT COALESCE(SUM(m.item_price * bi.quantity), 0) as total
            FROM Bill_Items bi
            JOIN Menu m ON bi.item_id = m.item_id
        """)
        total_revenue = cursor.fetchone()["total"]

        # Today revenue
        cursor.execute("""
            SELECT COALESCE(SUM(m.item_price * bi.quantity), 0) as total
            FROM Bill_Items bi
            JOIN Menu m ON bi.item_id = m.item_id
            JOIN Bills b ON bi.bill_id = b.bill_id
            WHERE DATE(b.bill_time) = ?
        """, (current_date,))
        revenue_today = cursor.fetchone()["total"]

        # Week revenue
        cursor.execute("""
            SELECT COALESCE(SUM(m.item_price * bi.quantity), 0) as total
            FROM Bill_Items bi
            JOIN Menu m ON bi.item_id = m.item_id
            JOIN Bills b ON bi.bill_id = b.bill_id
            WHERE DATE(b.bill_time) >= ?
        """, (current_week_start,))
        revenue_week = cursor.fetchone()["total"]

        # Month revenue
        cursor.execute("""
            SELECT COALESCE(SUM(m.item_price * bi.quantity), 0) as total
            FROM Bill_Items bi
            JOIN Menu m ON bi.item_id = m.item_id
            JOIN Bills b ON bi.bill_id = b.bill_id
            WHERE DATE(b.bill_time) >= ?
        """, (current_month_start,))
        revenue_month = cursor.fetchone()["total"]

        # Breakdown by payment method
        cursor.execute("""
            SELECT COALESCE(b.payment_method, 'Unspecified') as method,
                   COUNT(b.bill_id) as bills_count,
                   COALESCE(SUM(m.item_price * bi.quantity), 0) as total
            FROM Bills b
            LEFT JOIN Bill_Items bi ON b.bill_id = bi.bill_id
            LEFT JOIN Menu m ON bi.item_id = m.item_id
            WHERE b.payment_time IS NOT NULL
            GROUP BY b.payment_method
        """)
        payment_methods = [dict(r) for r in cursor.fetchall()]

        # Category revenue breakdown
        cursor.execute("""
            SELECT m.item_category,
                   COALESCE(SUM(m.item_price * bi.quantity), 0) as total
            FROM Bill_Items bi
            JOIN Menu m ON bi.item_id = m.item_id
            GROUP BY m.item_category
            ORDER BY total DESC
        """)
        category_revenue = [dict(r) for r in cursor.fetchall()]

        return {
            "total_revenue": round(total_revenue, 2),
            "revenue_today": round(revenue_today, 2),
            "revenue_this_week": round(revenue_week, 2),
            "revenue_this_month": round(revenue_month, 2),
            "payment_methods": payment_methods,
            "category_revenue": category_revenue
        }

@router.get("/sales")
def get_item_sales(sort_order: str = Query("desc")):
    with get_db() as conn:
        cursor = conn.cursor()
        order_dir = "ASC" if sort_order.lower() == "asc" else "DESC"

        query = f"""
            SELECT m.item_name, m.item_category, m.item_type,
                   COALESCE(SUM(bi.quantity), 0) AS total_quantity,
                   COALESCE(SUM(bi.quantity * m.item_price), 0) AS total_sales
            FROM Bill_Items bi
            JOIN Menu m ON bi.item_id = m.item_id
            GROUP BY m.item_name
            ORDER BY total_quantity {order_dir}
        """
        cursor.execute(query)
        items = [dict(r) for r in cursor.fetchall()]

        # Breakdown top items per category
        by_category = {}
        for item in items:
            cat = item["item_category"] or "Other"
            if cat not in by_category:
                by_category[cat] = []
            if len(by_category[cat]) < 7: # Top 7 per category
                by_category[cat].append(item)

        return {
            "items": items,
            "by_category": by_category
        }

@router.get("/member-profile/{member_id}")
def get_member_profile_stats(member_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT member_id, member_name, points FROM Memberships WHERE member_id = ?", (member_id,))
        member = cursor.fetchone()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        cursor.execute("""
            SELECT m.item_name, m.item_category, SUM(bi.quantity) AS order_count
            FROM Bill_Items bi
            JOIN Menu m ON bi.item_id = m.item_id
            JOIN Bills b ON bi.bill_id = b.bill_id
            WHERE b.member_id = ?
            GROUP BY bi.item_id
            ORDER BY order_count DESC
        """, (member_id,))
        ordered_items = [dict(r) for r in cursor.fetchall()]

        top_5 = ordered_items[:5]

        return {
            "member_id": member["member_id"],
            "member_name": member["member_name"],
            "points": member["points"],
            "ordered_items": ordered_items,
            "top_5": top_5
        }
