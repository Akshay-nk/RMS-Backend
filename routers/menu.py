from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from database import get_db
from models import MenuItemCreate, MenuItemUpdate

router = APIRouter(prefix="/api/menu", tags=["menu"])

@router.get("/")
def get_menu(
    category: Optional[str] = Query(None),
    item_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM Menu WHERE 1=1"
        params = []

        if category:
            query += " AND item_category = ?"
            params.append(category)

        if item_type:
            query += " AND item_type = ?"
            params.append(item_type)

        if search:
            query += " AND (item_type LIKE ? OR item_category LIKE ? OR item_name LIKE ? OR item_id LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term, term])

        query += " ORDER BY item_id"
        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        return rows

@router.get("/categories")
def get_categories():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT item_category FROM Menu ORDER BY item_category")
        categories = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT item_type FROM Menu ORDER BY item_type")
        types = [row[0] for row in cursor.fetchall()]
        return {"categories": categories, "types": types}

@router.get("/{item_id}")
def get_menu_item(item_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Menu WHERE item_id = ?", (item_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")
        return dict(row)

@router.post("/")
def create_menu_item(item: MenuItemCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT item_id FROM Menu WHERE item_id = ?", (item.item_id,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Item ID already exists")

        cursor.execute(
            """
            INSERT INTO Menu (item_id, item_name, item_type, item_category, item_price, item_description)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item.item_id, item.item_name, item.item_type, item.item_category, item.item_price, item.item_description)
        )
        return {"success": True, "message": "Menu item created successfully", "item_id": item.item_id}

@router.put("/{item_id}")
def update_menu_item(item_id: str, item: MenuItemUpdate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE Menu
            SET item_name = ?, item_type = ?, item_category = ?, item_price = ?, item_description = ?
            WHERE item_id = ?
            """,
            (item.item_name, item.item_type, item.item_category, item.item_price, item.item_description, item_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"success": True, "message": "Menu item updated successfully"}

@router.delete("/{item_id}")
def delete_menu_item(item_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Menu WHERE item_id = ?", (item_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"success": True, "message": "Menu item deleted successfully"}
