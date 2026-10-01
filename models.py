from pydantic import BaseModel, EmailStr
from typing import Optional, List

# Auth Models
class CustomerRegisterRequest(BaseModel):
    member_name: str
    email: str
    phone_number: str
    password: str

class CustomerLoginRequest(BaseModel):
    email: str
    password: str

class StaffLoginRequest(BaseModel):
    account_id: int
    password: str

class AdminVerifyRequest(BaseModel):
    admin_id: str
    password: str

# Menu Models
class MenuItemBase(BaseModel):
    item_id: str
    item_name: str
    item_type: str
    item_category: str
    item_price: float
    item_description: Optional[str] = ""

class MenuItemCreate(MenuItemBase):
    pass

class MenuItemUpdate(BaseModel):
    item_name: str
    item_type: str
    item_category: str
    item_price: float
    item_description: Optional[str] = ""

# Table Models
class TableCreate(BaseModel):
    table_id: int
    capacity: int
    is_available: Optional[int] = 1

# Reservation Models
class ReservationCreate(BaseModel):
    customer_name: str
    table_id: int
    reservation_time: str
    reservation_date: str
    head_count: int
    special_request: Optional[str] = ""

# POS & Billing Models
class AddToCartRequest(BaseModel):
    table_id: int
    item_id: str
    quantity: int
    bill_id: Optional[int] = None

class DeleteCartItemRequest(BaseModel):
    bill_item_id: int
    bill_id: int
    table_id: int
    item_id: str

class CashPaymentRequest(BaseModel):
    bill_id: int
    staff_id: int
    member_id: Optional[int] = 1
    reservation_id: Optional[int] = None
    payment_amount: float

class CardPaymentRequest(BaseModel):
    bill_id: int
    staff_id: int
    member_id: Optional[int] = 1
    reservation_id: Optional[int] = None
    account_holder_name: str
    card_number: str
    expiry_date: str
    security_code: str

# Management Models
class StaffCreate(BaseModel):
    staff_name: str
    role: str
    account_id: int

class StaffUpdate(BaseModel):
    staff_name: str
    role: str
    account_id: int

class MemberCreate(BaseModel):
    member_name: str
    account_id: int
    points: Optional[int] = 0

class AccountCreate(BaseModel):
    email: str
    phone_number: str
    password: str
