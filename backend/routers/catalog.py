from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from .. import models, schemas
from .admin_auth import require_admin

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/categories", response_model=list[schemas.CategoryOut])
def list_categories(species: Optional[models.PetSpecies] = None, db: Session = Depends(get_db)):
    q = db.query(models.Category).filter(models.Category.is_active == True)  # noqa: E712
    if species:
        q = q.filter((models.Category.species == species) | (models.Category.species == None))  # noqa: E712
    return q.order_by(models.Category.sort_order).all()


@router.post("/categories", response_model=schemas.CategoryOut, dependencies=[Depends(require_admin)])
def create_category(payload: schemas.CategoryIn, db: Session = Depends(get_db)):
    cat = models.Category(**payload.dict())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.get("/products/brands", response_model=list[str])
def list_brands(db: Session = Depends(get_db)):
    rows = (
        db.query(models.Product.brand)
        .filter(models.Product.is_active == True, models.Product.brand.isnot(None))  # noqa: E712
        .distinct()
        .order_by(models.Product.brand)
        .all()
    )
    return [r[0] for r in rows]


@router.get("/products", response_model=list[schemas.ProductOut])
def list_products(
    category_id: Optional[int] = None,
    species: Optional[models.PetSpecies] = None,
    food_type: Optional[models.FoodType] = None,
    composition: Optional[List[str]] = Query(None),
    brand: Optional[List[str]] = Query(None),
    age_group: Optional[List[models.AgeGroup]] = Query(None),
    sterilization: Optional[models.Sterilization] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Product).filter(models.Product.is_active == True)  # noqa: E712
    if category_id:
        q = q.filter(models.Product.category_id == category_id)
    if species:
        q = q.filter(models.Product.species == species)
    if food_type:
        q = q.filter(models.Product.food_type == food_type)
    if composition:
        q = q.filter(
            or_(*[models.Product.composition.like(f"%{token}%") for token in composition])
        )
    if brand:
        q = q.filter(models.Product.brand.in_(brand))
    if age_group:
        q = q.filter(models.Product.age_group.in_(age_group))
    if sterilization:
        q = q.filter(models.Product.sterilization == sterilization)
    return q.all()


@router.get("/products/{product_id}/variants", response_model=list[schemas.ProductVariantOut])
def list_variants(product_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.ProductVariant)
        .filter(models.ProductVariant.product_id == product_id)
        .all()
    )


@router.post(
    "/products/{product_id}/variants",
    response_model=schemas.ProductVariantOut,
    dependencies=[Depends(require_admin)],
)
def create_variant(product_id: int, payload: schemas.ProductVariantIn, db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")
    variant = models.ProductVariant(product_id=product_id, **payload.dict())
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.delete("/products/{product_id}/variants/{variant_id}", dependencies=[Depends(require_admin)])
def delete_variant(product_id: int, variant_id: int, db: Session = Depends(get_db)):
    variant = (
        db.query(models.ProductVariant)
        .filter_by(id=variant_id, product_id=product_id)
        .first()
    )
    if not variant:
        raise HTTPException(404, "Variant topilmadi")
    db.delete(variant)
    db.commit()
    return {"ok": True}


@router.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")
    return product


@router.post("/products", response_model=schemas.ProductOut, dependencies=[Depends(require_admin)])
def create_product(payload: schemas.ProductIn, db: Session = Depends(get_db)):
    product = models.Product(**payload.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=schemas.ProductOut, dependencies=[Depends(require_admin)])
def update_product(product_id: int, payload: schemas.ProductIn, db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")
    for k, v in payload.dict().items():
        setattr(product, k, v)
    db.commit()
    db.refresh(product)
    return product


MAX_IMAGE_BYTES = 5 * 1024 * 1024

# Kengaytma faqat shu ro'yxatdan olinadi — mijoz yuborgan fayl nomiga va
# `Content-Type` headeriga ishonmaymiz (ikkisi ham soxtalashtirilishi mumkin
# edi: `evil.html` + `Content-Type: image/png` bir xil originda bajariladigan
# HTML fayl yaratardi).
_ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".webp", ".gif")


def _detect_image_ext(contents: bytes) -> Optional[str]:
    """Fayl imzosi (magic bytes) bo'yicha kengaytmani aniqlaydi."""
    if contents.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if contents.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if contents[:4] == b"RIFF" and contents[8:12] == b"WEBP":
        return ".webp"
    if contents[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    return None  # SVG, HTML va boshqa bajarilishi mumkin bo'lgan formatlar


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    """Faylni bo'lak-bo'lak o'qiydi va limitdan oshsa darhol to'xtatadi.

    Avval `await file.read()` butun tanani xotiraga yuklab, keyin hajmini
    tekshirardi — 2GB yuklama to'liq xotirada bo'lardi.
    """
    chunks = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(400, "Rasm hajmi 5MB dan oshmasligi kerak")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/products/{product_id}/image")
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: models.Admin = Depends(require_admin),
):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")

    contents = await _read_limited(file, MAX_IMAGE_BYTES)
    if not contents:
        raise HTTPException(400, "Bo'sh fayl yuborildi")

    ext = _detect_image_ext(contents)
    if not ext:
        raise HTTPException(400, "Faqat PNG, JPG, WEBP yoki GIF rasmlar yuklash mumkin")

    upload_dir = Path(__file__).parent.parent / "uploads"
    upload_dir.mkdir(exist_ok=True)

    # Eski nusxalarni tozalaymiz — kengaytma o'zgarganda avval yetim fayl qolardi
    for old_ext in _ALLOWED_IMAGE_EXTS:
        old_path = upload_dir / f"product-{product_id}{old_ext}"
        if old_path != upload_dir / f"product-{product_id}{ext}" and old_path.exists():
            old_path.unlink()

    filename = f"product-{product_id}{ext}"
    with open(upload_dir / filename, "wb") as f:
        f.write(contents)

    product.image_url = f"uploads/{filename}"
    db.commit()
    db.refresh(product)

    return {"image_url": product.image_url}


@router.delete("/products/{product_id}", dependencies=[Depends(require_admin)])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")
    product.is_active = False
    db.commit()
    return {"ok": True}
