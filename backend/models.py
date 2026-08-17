"""
ZooPet platformasi uchun SQLAlchemy modellari.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class OrderStatus(str, enum.Enum):
    NEW = "new"                 # yangi buyurtma
    CONFIRMED = "confirmed"     # tasdiqlangan
    PACKING = "packing"         # yig'ilmoqda
    DELIVERING = "delivering"   # yetkazilmoqda
    DELIVERED = "delivered"     # yetkazib berildi
    CANCELLED = "cancelled"     # bekor qilingan


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CLICK = "click"
    PAYME = "payme"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"


class SubscriptionTier(str, enum.Enum):
    EKO = "eko"
    BASIC = "basic"
    PLUS = "plus"
    PREMIUM = "premium"


class PetSpecies(str, enum.Enum):
    CAT = "cat"
    DOG = "dog"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class FoodType(str, enum.Enum):
    DRY = "dry"
    WET = "wet"


class AgeGroup(str, enum.Enum):
    ADULT = "adult"
    YOUNG = "young"
    SENIOR = "senior"


class Sterilization(str, enum.Enum):
    STERILIZED = "sterilized"
    NOT_STERILIZED = "not_sterilized"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    icon = Column(String(10), default="🐾")  # emoji ikonka, tez ko'rinish uchun
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    species = Column(Enum(PetSpecies), nullable=True)  # null = shared, "cat" = only cat, "dog" = only dog

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    price = Column(Float, nullable=False)          # so'mda
    old_price = Column(Float, nullable=True)        # chegirma ko'rsatish uchun
    image_url = Column(String(200), default="")
    stock = Column(Integer, default=100)
    unit = Column(String(30), default="dona")       # dona, kg, paket...
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    species = Column(Enum(PetSpecies), nullable=True)
    brand = Column(String(100), nullable=True)
    food_type = Column(Enum(FoodType), nullable=True)
    age_group = Column(Enum(AgeGroup), nullable=True)
    composition = Column(String(200), nullable=True)  # comma-separated: meat,fish,poultry,vegetables_grain
    sterilization = Column(Enum(Sterilization), nullable=True)

    category = relationship("Category", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product",
                             cascade="all, delete-orphan", order_by="ProductVariant.id")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    label = Column(String(50), nullable=False)   # "100g", "1kg" kabi, erkin matn
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=True)        # bo'sh = kuzatilmaydi

    product = relationship("Product", back_populates="variants")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    phone = Column(String(30), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    address = Column(String(400), default="")  # oxirgi yetkazib berish manzili (checkoutni to'ldirish uchun)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="customer")
    subscriptions = relationship("Subscription", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.NEW)
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.CASH)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    delivery_address = Column(String(400), default="")
    delivery_phone = Column(String(30), default="")
    comment = Column(String(400), default="")
    total_amount = Column(Float, default=0)
    delivery_fee = Column(Float, default=15000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String(200))   # buyurtma vaqtidagi nomi (tarix uchun)
    unit_price = Column(Float)           # buyurtma vaqtidagi narxi
    quantity = Column(Integer, default=1)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True)
    tier = Column(Enum(SubscriptionTier), nullable=False)
    species = Column(Enum(PetSpecies), nullable=False)
    name = Column(String(80), nullable=False)          # "EKO", "BASIC", "PLUS", "PREMIUM"
    price = Column(Float, nullable=False)              # so'm/oy
    description = Column(Text, default="")             # kiritilgan xizmatlar ro'yxati (erkin matn)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    cancelled_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    telegram_id = Column(String(50), nullable=True)  # buyurtma bildirishnomalari uchun
