from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..notify import notify_admin_new_order
from .. import customer_auth
from .admin_auth import require_admin

router = APIRouter(prefix="/api", tags=["orders"])

DELIVERY_FEE = 15000  # so'm, sodda qat'iy tarif (keyinchalik hudud bo'yicha o'zgartirish mumkin)

# Buyurtma holati oldinga (yoki bekor qilishga) qarab harakatlanadi. Avval
# faqat qiymat enumda borligi tekshirilardi, shuning uchun `delivered → new`
# yoki `cancelled → delivering` kabi o'tishlar ham qabul qilinardi.
_ALLOWED_TRANSITIONS = {
    models.OrderStatus.NEW: {models.OrderStatus.CONFIRMED, models.OrderStatus.CANCELLED},
    models.OrderStatus.CONFIRMED: {models.OrderStatus.PACKING, models.OrderStatus.CANCELLED},
    models.OrderStatus.PACKING: {models.OrderStatus.DELIVERING, models.OrderStatus.CANCELLED},
    models.OrderStatus.DELIVERING: {models.OrderStatus.DELIVERED, models.OrderStatus.CANCELLED},
    models.OrderStatus.DELIVERED: set(),   # yakuniy holat
    models.OrderStatus.CANCELLED: set(),   # yakuniy holat
}


@router.post("/orders", response_model=schemas.OrderOut)
def create_order(
    payload: schemas.OrderCreate,
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(customer_auth.get_current_customer),
):
    if not payload.items:
        raise HTTPException(400, "Savat bo'sh")

    order = models.Order(
        customer_id=customer.id,
        payment_method=payload.payment_method,
        delivery_address=payload.address,
        delivery_phone=customer.phone,
        comment=payload.comment,
        delivery_fee=DELIVERY_FEE,
    )
    db.add(order)
    db.flush()

    total = 0.0
    for item in payload.items:
        product = db.query(models.Product).get(item.product_id)
        if not product or not product.is_active:
            raise HTTPException(400, f"Mahsulot topilmadi: {item.product_id}")
        # Avval `continue` edi: barcha miqdorlar 0 bo'lsa, mahsulotsiz buyurtma
        # yaratilib, mijozdan faqat yetkazib berish narxi olinardi.
        if item.quantity < 1:
            raise HTTPException(400, "Mahsulot miqdori kamida 1 bo'lishi kerak")

        unit_price = product.price
        product_name = product.name
        if item.variant_id:
            variant = db.query(models.ProductVariant).filter_by(
                id=item.variant_id, product_id=product.id
            ).first()
            if not variant:
                raise HTTPException(400, f"Variant topilmadi: {item.variant_id}")
            unit_price = variant.price
            product_name = f"{product.name} ({variant.label})"
        elif product.variants:
            raise HTTPException(400, f"Iltimos, {product.name} uchun variantni tanlang")

        line_total = unit_price * item.quantity
        total += line_total
        db.add(
            models.OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product_name,
                unit_price=unit_price,
                quantity=item.quantity,
            )
        )

    order.total_amount = total + DELIVERY_FEE
    customer.address = payload.address  # keyingi safar checkoutni to'ldirish uchun
    db.commit()
    db.refresh(order)

    notify_admin_new_order(order)

    return order


@router.get("/orders", response_model=list[schemas.OrderOut], dependencies=[Depends(require_admin)])
def list_orders(
    status: Optional[models.OrderStatus] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Faqat admin uchun. Avval autentifikatsiyasiz ishlab, barcha mijozlarning
    manzili va telefon raqamini ochiq qaytarardi."""
    q = db.query(models.Order).order_by(models.Order.created_at.desc())
    if status:
        q = q.filter(models.Order.status == status)
    return q.offset(offset).limit(limit).all()


@router.get("/orders/{order_id}", response_model=schemas.OrderOut, dependencies=[Depends(require_admin)])
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Faqat admin uchun. Mijoz o'z buyurtmalarini `/api/customer/orders` dan oladi."""
    order = db.query(models.Order).get(order_id)
    if not order:
        raise HTTPException(404, "Buyurtma topilmadi")
    return order


@router.patch(
    "/orders/{order_id}/status",
    response_model=schemas.OrderOut,
    dependencies=[Depends(require_admin)],
)
def update_order_status(order_id: int, payload: schemas.OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(models.Order).get(order_id)
    if not order:
        raise HTTPException(404, "Buyurtma topilmadi")

    # Status qiymati endi Pydantic darajasida `models.OrderStatus` bo'yicha
    # tekshiriladi (422), shuning uchun bu yerda qo'lda ro'yxat solishtirish
    # kerak emas. Buning o'rniga o'tish qoidasini tekshiramiz.
    current = models.OrderStatus(order.status)
    new_status = payload.status
    if new_status != current and new_status not in _ALLOWED_TRANSITIONS[current]:
        raise HTTPException(
            400,
            f"'{current.value}' holatidan '{new_status.value}' holatiga o'tish mumkin emas",
        )

    order.status = new_status
    db.commit()
    db.refresh(order)
    return order
