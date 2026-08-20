"""
Test/namuna ma'lumotlar bilan bazani to'ldirish.

Ishga tushirish:
    python -m backend.seed
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from .database import DATABASE_URL, SessionLocal, engine
from . import models

if DATABASE_URL.startswith("sqlite"):
    models.Base.metadata.create_all(bind=engine)
else:
    print("ℹ️ PostgreSQL tanlandi: avval 'alembic upgrade head' ni ishga tushiring.")

db = SessionLocal()

if db.query(models.Category).count() == 0:
    S = models.PetSpecies
    categories = [
        models.Category(name="It ozig'i", icon="🐶", sort_order=1, species=S.DOG),
        models.Category(name="Mushuk ozig'i", icon="🐱", sort_order=2, species=S.CAT),
        models.Category(name="Aksessuarlar", icon="🦴", sort_order=3),
        models.Category(name="Vitaminlar", icon="💊", sort_order=4),
        models.Category(name="Tuvaklar va to'ldiruvchilar", icon="🪣", sort_order=5),
    ]
    db.add_all(categories)
    db.commit()
    for c in categories:
        db.refresh(c)

    dog_food, cat_food, accessories, vitamins, litter_boxes = categories

    FT = models.FoodType
    AG = models.AgeGroup
    ST = models.Sterilization

    products = [
        models.Product(category_id=dog_food.id, name="Royal Canin Adult",
                        description="Kattalar uchun quruq it ozig'i", price=185000, old_price=210000,
                        image_url="", stock=25, unit="paket",
                        species=S.DOG, brand="Royal Canin", food_type=FT.DRY, age_group=AG.ADULT, composition="meat", sterilization=ST.NOT_STERILIZED),
        models.Product(category_id=dog_food.id, name="Pedigree kichik itlar uchun",
                        description="Kichik zotdagi itlar uchun", price=95000,
                        image_url="", stock=40, unit="paket",
                        species=S.DOG, brand="Pedigree", food_type=FT.DRY, age_group=AG.YOUNG, composition="poultry", sterilization=ST.NOT_STERILIZED),
        models.Product(category_id=cat_food.id, name="Whiskas mushuk ozig'i 1.9kg",
                        description="Voyaga yetgan mushuklar uchun", price=78000,
                        image_url="", stock=35, unit="paket",
                        species=S.CAT, brand="Whiskas", food_type=FT.DRY, age_group=AG.ADULT, composition="meat,poultry", sterilization=ST.NOT_STERILIZED),
        models.Product(category_id=cat_food.id, name="Kitekat balik ta'mida 350g",
                        description="Konservalangan mushuk ozig'i", price=18000,
                        image_url="", stock=60, unit="dona",
                        species=S.CAT, brand="Kitekat", food_type=FT.WET, age_group=AG.ADULT, composition="fish", sterilization=ST.NOT_STERILIZED),
        models.Product(category_id=accessories.id, name="Rezina suyak o'yinchoq",
                        description="Itlar uchun chaynash o'yinchog'i", price=32000,
                        image_url="", stock=50, unit="dona",
                        species=S.DOG),
        models.Product(category_id=accessories.id, name="Mushuk uchun laser o'yinchoq",
                        description="Interaktiv lazer ko'rsatkich", price=45000,
                        image_url="", stock=20, unit="dona",
                        species=S.CAT),
        models.Product(category_id=accessories.id, name="Bo'yinbog' (o'rtacha)",
                        description="Sozlanadigan bo'yinbog'", price=55000,
                        image_url="", stock=30, unit="dona"),
        models.Product(category_id=accessories.id, name="Oziq-ovqat idishi (metall)",
                        description="Zanglamaydigan po'lat, 500ml", price=42000,
                        image_url="", stock=45, unit="dona"),
        models.Product(category_id=vitamins.id, name="It uchun shampun 250ml",
                        description="Barcha teri turlari uchun", price=38000,
                        image_url="", stock=28, unit="dona",
                        species=S.DOG),
        models.Product(category_id=vitamins.id, name="Mushuk toza qumi 5L",
                        description="Hidni yutuvchi bentonit qum", price=52000,
                        image_url="", stock=33, unit="paket",
                        species=S.CAT),
        models.Product(category_id=vitamins.id, name="Farmina N&D mus'qlari uchun vitamin 60t",
                        description="Iloviy mineral va vitaminlar", price=98000,
                        image_url="", stock=20, unit="dona",
                        species=S.CAT, brand="Farmina"),
        models.Product(category_id=vitamins.id, name="Felix it'lar uchun vitamin 100ml",
                        description="Husniy travolari bilan", price=76000,
                        image_url="", stock=18, unit="dona",
                        species=S.DOG, brand="Felix"),
        models.Product(category_id=litter_boxes.id, name="Mushuk tuvali (yoshira)",
                        description="Yashira tuvali, 2.5kg", price=42000,
                        image_url="", stock=25, unit="dona",
                        species=S.CAT, brand="Beige"),
        models.Product(category_id=litter_boxes.id, name="It uchun yastiq to'plama",
                        description="Poliester yastiq, L o'lchov", price=185000,
                        image_url="", stock=15, unit="dona",
                        species=S.DOG, brand="Darling"),
        models.Product(category_id=cat_food.id, name="Gemon keksalar uchun ozig'i 400g",
                        description="Voyaga bo'lgan mushuklar uchun", price=28000,
                        image_url="", stock=22, unit="dona",
                        species=S.CAT, brand="Gemon", food_type=FT.DRY, age_group=AG.SENIOR, composition="meat,vegetables_grain", sterilization=ST.NOT_STERILIZED),
        models.Product(category_id=cat_food.id, name="Royal Canin Sterilised mushuklar uchun 400g",
                        description="Sterilizatsiyadan o'tgan mushuklar uchun maxsus ratsion", price=112000,
                        image_url="", stock=20, unit="dona",
                        species=S.CAT, brand="Royal Canin", food_type=FT.DRY, age_group=AG.ADULT, composition="meat", sterilization=ST.STERILIZED),
        models.Product(category_id=dog_food.id, name="Pedigree Sterilised itlar uchun 2.5kg",
                        description="Sterilizatsiyadan o'tgan itlar uchun", price=110000,
                        image_url="", stock=18, unit="paket",
                        species=S.DOG, brand="Pedigree", food_type=FT.DRY, age_group=AG.ADULT, composition="poultry", sterilization=ST.STERILIZED),
    ]
    db.add_all(products)
    db.commit()
    for p in products:
        db.refresh(p)

    royal_canin_adult = products[0]
    pedigree_small = products[1]

    variants = [
        models.ProductVariant(product_id=royal_canin_adult.id, label="1kg", price=75000, stock=30),
        models.ProductVariant(product_id=royal_canin_adult.id, label="3kg", price=185000, stock=25),
        models.ProductVariant(product_id=royal_canin_adult.id, label="8kg", price=420000, stock=15),
        models.ProductVariant(product_id=pedigree_small.id, label="500g", price=45000, stock=50),
        models.ProductVariant(product_id=pedigree_small.id, label="2kg", price=95000, stock=40),
        models.ProductVariant(product_id=pedigree_small.id, label="10kg", price=380000, stock=20),
    ]
    db.add_all(variants)
    db.commit()

    print(f"✅ {len(categories)} kategoriya, {len(products)} mahsulot va {len(variants)} variant qo'shildi.")
else:
    print("ℹ️ Kategoriyalar allaqachon mavjud, hech narsa qo'shilmadi.")

if db.query(models.SubscriptionPlan).count() == 0:
    T = models.SubscriptionTier
    S = models.PetSpecies
    plans = [
        # Mushuklar uchun 4 ta tarif
        models.SubscriptionPlan(tier=T.EKO, species=S.CAT, name="EKO", price=185000, sort_order=1,
                                 description="Sifatli yevropa ovqati (Club 4 Paws) bilan eng qulay boshlanish."),
        models.SubscriptionPlan(tier=T.BASIC, species=S.CAT, name="BASIC", price=245000, sort_order=2,
                                 description="Premium ovqat + napolnitel + haftalik bepul yetkazish."),
        models.SubscriptionPlan(tier=T.PLUS, species=S.CAT, name="PLUS", price=430000, sort_order=3,
                                 description="BASIC + oyiga bir marta uyda professional grooming."),
        models.SubscriptionPlan(tier=T.PREMIUM, species=S.CAT, name="PREMIUM", price=600000, sort_order=4,
                                 description="To'liq g'amxo'rlik: parazit himoyasi, vet nazorati, operatsiyaga chegirma."),
        # Itlar uchun 3 ta tarif (ovqat hajmi kattaroq bo'lgani uchun EKO taklif qilinmaydi)
        models.SubscriptionPlan(tier=T.BASIC, species=S.DOG, name="BASIC", price=440000, sort_order=2,
                                 description="Premium ovqat + napolnitel + haftalik bepul yetkazish."),
        models.SubscriptionPlan(tier=T.PLUS, species=S.DOG, name="PLUS", price=610000, sort_order=3,
                                 description="BASIC + oyiga bir marta uyda professional grooming."),
        models.SubscriptionPlan(tier=T.PREMIUM, species=S.DOG, name="PREMIUM", price=850000, sort_order=4,
                                 description="To'liq g'amxo'rlik: parazit himoyasi, vet nazorati, operatsiyaga chegirma."),
    ]
    db.add_all(plans)
    db.commit()
    print(f"✅ {len(plans)} ta obuna tarifi qo'shildi.")
else:
    print("ℹ️ Obuna tariflari allaqachon mavjud, hech narsa qo'shilmadi.")

db.close()
