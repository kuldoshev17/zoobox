from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from .. import customer_auth
from ..notify import notify_admin_new_subscription
from .admin_auth import require_admin

router = APIRouter(prefix="/api", tags=["subscriptions"])


@router.get("/subscription-plans", response_model=list[schemas.SubscriptionPlanOut])
def list_plans(species: Optional[models.PetSpecies] = None, db: Session = Depends(get_db)):
    q = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.is_active == True)  # noqa: E712
    if species:
        q = q.filter(models.SubscriptionPlan.species == species)
    return q.order_by(models.SubscriptionPlan.sort_order).all()


def _get_active_subscription(db: Session, customer: models.Customer):
    return (
        db.query(models.Subscription)
        .filter(
            models.Subscription.customer_id == customer.id,
            models.Subscription.status == models.SubscriptionStatus.ACTIVE,
        )
        .first()
    )


@router.get("/customer/subscription", response_model=Optional[schemas.SubscriptionOut])
def my_subscription(
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(customer_auth.get_current_customer),
):
    return _get_active_subscription(db, customer)


@router.post("/customer/subscription", response_model=schemas.SubscriptionOut)
def create_subscription(
    payload: schemas.SubscriptionCreate,
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(customer_auth.get_current_customer),
):
    if _get_active_subscription(db, customer):
        raise HTTPException(409, "Sizda allaqachon faol obuna mavjud")

    plan = db.query(models.SubscriptionPlan).get(payload.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(404, "Tarif topilmadi")

    subscription = models.Subscription(customer_id=customer.id, plan_id=plan.id)
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    notify_admin_new_subscription(subscription)

    return subscription


@router.delete("/customer/subscription/{subscription_id}", response_model=schemas.SubscriptionOut)
def cancel_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    customer: models.Customer = Depends(customer_auth.get_current_customer),
):
    subscription = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.id == subscription_id,
            models.Subscription.customer_id == customer.id,
        )
        .first()
    )
    if not subscription:
        raise HTTPException(404, "Obuna topilmadi")

    subscription.status = models.SubscriptionStatus.CANCELLED
    subscription.cancelled_at = datetime.utcnow()
    db.commit()
    db.refresh(subscription)
    return subscription


@router.get(
    "/admin/subscriptions",
    response_model=list[schemas.SubscriptionAdminOut],
    dependencies=[Depends(require_admin)],
)
def list_all_subscriptions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Faqat admin uchun. Avval autentifikatsiyasiz ishlab, barcha obunachilarning
    ismi va telefon raqamini ochiq qaytarardi (`SubscriptionAdminOut` → `CustomerOut`)."""
    return (
        db.query(models.Subscription)
        .order_by(models.Subscription.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
