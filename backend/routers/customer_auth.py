from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from .. import customer_auth
from .. import telegram_auth

router = APIRouter(prefix="/api/customer", tags=["customer"])


@router.post("/register", response_model=schemas.CustomerAuthOut)
def register(
    payload: schemas.CustomerRegister,
    db: Session = Depends(get_db),
    telegram_user: dict = Depends(telegram_auth.get_telegram_user),
):
    telegram_id = str(telegram_user["id"])
    phone = customer_auth.normalize_phone(payload.phone)

    existing = (
        db.query(models.Customer)
        .filter(
            (models.Customer.telegram_id == telegram_id)
            | (models.Customer.phone == phone)
        )
        .first()
    )
    if existing:
        raise HTTPException(409, "Bu telefon yoki Telegram hisobi allaqachon ro'yxatdan o'tgan")

    customer = models.Customer(
        telegram_id=telegram_id,
        phone=phone,
        full_name=payload.full_name,
        password_hash=customer_auth.hash_password(payload.password),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    return {"token": customer_auth.create_token(customer.id), "customer": customer}


@router.post("/login", response_model=schemas.CustomerAuthOut)
def login(payload: schemas.CustomerLogin, db: Session = Depends(get_db)):
    phone = customer_auth.normalize_phone(payload.phone)
    customer = db.query(models.Customer).filter(models.Customer.phone == phone).first()
    if not customer or not customer_auth.verify_password(payload.password, customer.password_hash):
        raise HTTPException(401, "Telefon yoki parol xato")

    return {"token": customer_auth.create_token(customer.id), "customer": customer}


@router.get("/me", response_model=schemas.CustomerAuthOut)
def me(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if authorization and authorization.startswith("Bearer "):
        customer = customer_auth.get_current_customer(authorization, db)
        return {"token": authorization[len("Bearer "):], "customer": customer}

    # Bearer token yo'q — Telegram initData orqali avtomatik tanib olishga urinamiz
    telegram_user = telegram_auth.get_telegram_user(authorization)  # 401 agar tma yo'q/yaroqsiz
    customer = (
        db.query(models.Customer)
        .filter(models.Customer.telegram_id == str(telegram_user["id"]))
        .first()
    )
    if not customer:
        raise HTTPException(404, "Ro'yxatdan o'tilmagan")  # mijoz uchun ro'yxatdan o'tish belgisi

    return {"token": customer_auth.create_token(customer.id), "customer": customer}


@router.patch("/me", response_model=schemas.CustomerOut)
def update_me(
    payload: schemas.CustomerUpdate,
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(customer_auth.get_current_customer),
):
    if payload.full_name:
        customer.full_name = payload.full_name

    if payload.new_password:
        if not payload.current_password or not customer_auth.verify_password(
            payload.current_password, customer.password_hash
        ):
            raise HTTPException(401, "Joriy parol xato")
        if len(payload.new_password) < 8:
            raise HTTPException(400, "Yangi parol kamida 8 ta belgidan iborat bo'lishi kerak")
        customer.password_hash = customer_auth.hash_password(payload.new_password)

    db.commit()
    db.refresh(customer)
    return customer


@router.get("/orders", response_model=list[schemas.OrderOut])
def my_orders(
    customer: models.Customer = Depends(customer_auth.get_current_customer),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Order)
        .filter(models.Order.customer_id == customer.id)
        .order_by(models.Order.created_at.desc())
        .all()
    )
