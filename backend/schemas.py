"""
Pydantic sxemalari (API uchun kirish/chiqish formatlari).
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from . import models

# Pul so'mda (tiyinsiz) saqlanadi. `allow_inf_nan=False` muhim: `json.loads`
# bo'sh `NaN` / `Infinity` literallarini qabul qiladi, va bazaga tushgan NaN
# narx keyinchalik har bir `GET /api/products` javobini 500 ga aylantirardi
# (FastAPI `allow_nan=False` bilan serializatsiya qiladi) — ya'ni bitta so'rov
# butun katalogni ishdan chiqarardi.
_Money = Field(ge=0, le=1_000_000_000, allow_inf_nan=False)
_OptionalMoney = Field(default=None, ge=0, le=1_000_000_000, allow_inf_nan=False)


class CategoryOut(BaseModel):
    id: int
    name: str
    icon: str
    sort_order: int
    species: Optional[str] = None

    class Config:
        from_attributes = True


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: str = Field(default="🐾", max_length=8)
    sort_order: int = Field(default=0, ge=0, le=10_000)
    species: Optional[models.PetSpecies] = None


class ProductVariantOut(BaseModel):
    id: int
    label: str
    price: float
    stock: Optional[int] = None

    class Config:
        from_attributes = True


class ProductVariantIn(BaseModel):
    label: str = Field(min_length=1, max_length=50)
    price: float = _Money
    stock: Optional[int] = Field(default=None, ge=0, le=1_000_000)


class ProductOut(BaseModel):
    id: int
    category_id: int
    name: str
    description: str
    price: float
    old_price: Optional[float] = None
    image_url: str
    stock: int
    unit: str
    species: Optional[str] = None
    brand: Optional[str] = None
    food_type: Optional[str] = None
    composition: Optional[str] = None
    age_group: Optional[str] = None
    sterilization: Optional[str] = None
    variants: List[ProductVariantOut] = []

    class Config:
        from_attributes = True


class ProductIn(BaseModel):
    category_id: int
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    price: float = _Money
    old_price: Optional[float] = _OptionalMoney
    image_url: str = Field(default="", max_length=300)
    stock: int = Field(default=100, ge=0, le=1_000_000)
    unit: str = Field(default="dona", max_length=20)
    species: Optional[models.PetSpecies] = None
    brand: Optional[str] = Field(default=None, max_length=100)
    food_type: Optional[models.FoodType] = None
    composition: Optional[str] = Field(default=None, max_length=200)
    age_group: Optional[models.AgeGroup] = None
    sterilization: Optional[models.Sterilization] = None


class CartItemIn(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    # Avval chegara yo'q edi: `quantity: 2**62` jami summani cheksizlikka
    # olib chiqar va shu holatda bazaga yozilardi.
    quantity: int = Field(default=1, ge=1, le=1000)


class OrderCreate(BaseModel):
    # telegram_id/full_name/phone endi so'ralmaydi — ular ro'yxatdan o'tgan
    # mijozning autentifikatsiya qilingan hisobidan olinadi
    # (qarang: routers/orders.py create_order, customer_auth.py).
    address: str = Field(min_length=5, max_length=400)
    comment: str = Field(default="", max_length=400)
    payment_method: models.PaymentMethod = models.PaymentMethod.CASH
    items: List[CartItemIn] = Field(min_length=1, max_length=100)


class OrderItemOut(BaseModel):
    product_name: str
    unit_price: float
    quantity: int

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    status: str
    payment_method: str
    payment_status: str
    delivery_address: str
    delivery_phone: str
    comment: str
    total_amount: float
    delivery_fee: float
    created_at: datetime
    items: List[OrderItemOut]

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: models.OrderStatus


class AdminLogin(BaseModel):
    username: str
    password: str


class AdminPasswordChange(BaseModel):
    current_password: str
    new_password: str


class CustomerRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    phone: str = Field(min_length=9, max_length=30)
    # 8 belgilik minimum avval faqat brauzerda tekshirilardi — to'g'ridan-to'g'ri
    # API chaqiruvi bilan `password="1"` bilan ro'yxatdan o'tish mumkin edi.
    # 72 — bcrypt cheklovi (undan uzun parol jimgina qirqilardi).
    password: str = Field(min_length=8, max_length=72)


class CustomerLogin(BaseModel):
    phone: str = Field(min_length=9, max_length=30)
    password: str = Field(min_length=1, max_length=72)


class CustomerOut(BaseModel):
    id: int
    full_name: str
    phone: str
    address: str

    class Config:
        from_attributes = True


class CustomerAuthOut(BaseModel):
    token: str
    customer: CustomerOut


class CustomerUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    current_password: Optional[str] = Field(default=None, max_length=72)
    new_password: Optional[str] = Field(default=None, min_length=8, max_length=72)


class SubscriptionPlanOut(BaseModel):
    id: int
    tier: str
    species: str
    name: str
    price: float
    description: str

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    plan_id: int


class SubscriptionOut(BaseModel):
    id: int
    status: str
    created_at: datetime
    plan: SubscriptionPlanOut

    class Config:
        from_attributes = True


class SubscriptionAdminOut(SubscriptionOut):
    customer: CustomerOut
