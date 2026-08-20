# 🐾 ZooPet — Uy hayvonlari mahsulotlarini yetkazib berish platformasi

Zoo Planeta uslubidagi, lekin to'liq original kod bilan yozilgan platforma:
mahsulot katalogi, savat, buyurtma, to'lov (Click/Payme/naqd), Telegram bot,
web-do'kon va admin panel.

## Tarkibi

```
zoopet/
├── backend/          FastAPI server (API + SQLite/PostgreSQL baza)
│   ├── main.py        Ilova kirish nuqtasi
│   ├── models.py       Baza jadvallari
│   ├── schemas.py      API validatsiya sxemalari
│   ├── database.py     Baza ulanishi
│   ├── migrate_sqlite.py SQLite'dan PostgreSQL'ga import
│   ├── notify.py       Adminlarga Telegram orqali xabar yuborish
│   ├── seed.py          Namuna ma'lumotlar (test uchun)
│   └── routers/
│       ├── catalog.py     Kategoriya/mahsulot endpointlari
│       ├── orders.py      Buyurtma endpointlari
│       └── admin_auth.py  Admin login
├── bot/
│   └── main.py         Telegram bot (katalog, savat, checkout)
├── web/
│   ├── index.html       Mijozlar uchun veb-do'kon
│   └── admin/index.html Admin panel
├── payments/
│   ├── click.py          Click integratsiyasi (stub)
│   └── payme.py          Payme integratsiyasi (stub)
├── requirements.txt
└── .env.example
├── alembic.ini        PostgreSQL schema migration sozlamalari
└── migrations/        Alembic migrationlari
```

## O'rnatish

```bash
cd zoopet
pip install -r requirements.txt
cp .env.example .env    # keyin .env faylini o'z ma'lumotlaringiz bilan to'ldiring
```

`DATABASE_URL` bo'sh qoldirilsa, lokal ishlab chiqishda `backend/zoopet.db` SQLite bazasi ishlatiladi.
Production uchun PostgreSQL URL kiriting:

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/zoopet
```

## Ishga tushirish

**1. Bazani namuna ma'lumotlar bilan to'ldirish (bir marta):**
```bash
python -m backend.seed
```

PostgreSQL production bazasida avval schema migrationlarini ishga tushiring:

```bash
alembic upgrade head
python -m backend.seed
```

Mavjud SQLite ma'lumotlarini PostgreSQL'ga ko'chirish uchun PostgreSQL `DATABASE_URL` o'rnatilgan holda,
avval dry-run qiling, so'ng import qiling. Manba baza o'zgartirilmaydi va backup nusxasi yaratiladi:

```bash
python -m backend.migrate_sqlite --source backend/zoopet.db --dry-run
python -m backend.migrate_sqlite --source backend/zoopet.db
```

Importdan oldin `backend/zoopet.db` nusxasini saqlang. Production'da Alembic migrationlari server ishga
tushishidan oldin alohida release qadamida bajariladi; ilova startup paytida jadvallarni o'zi yaratmaydi.

**2. Backend serverni ishga tushirish:**
```bash
uvicorn backend.main:app --reload --port 8000
```
- Veb-do'kon: `http://127.0.0.1:8000/`
- Admin panel: `http://127.0.0.1:8000/admin/`
- API: `http://127.0.0.1:8000/api/...`

**3. Admin foydalanuvchi yaratish/parol almashtirish:**
```bash
python -m backend.create_admin
```
Interaktiv CLI orqali admin login va parol kiritiladi. Parol **hech qachon HTTP orqali uzatilmaydi** — faqat terminaldan kiritiladi. Allaqachon mavjud bo'lgan admin uchun parol almashtirishda ham shu skriptni ishlating.

Admin panelga kirishdan so'ng parolni `POST /api/admin/change-password` API orqali ham o'zgartirish mumkin.

**4. Telegram botni ishga tushirish (ixtiyoriy, alohida terminalda):**
```bash
export BOT_TOKEN=sizning_bot_tokeningiz   # yoki .env faylida
python -m bot.main
```
Bot tokenini olish uchun Telegram'da [@BotFather](https://t.me/BotFather) ga yozing.

## O'z logotipingizni qo'shish

- **Web-do'kon**: `web/index.html` faylida `<div class="logo">` ichidagi 🐾 emoji o'rniga o'z logo rasmingizni (`<img>`) qo'yishingiz mumkin.
- **Telegram bot**: BotFather orqali `/setuserpic` buyrug'i bilan bot rasmini o'rnatasiz.
- **Mahsulot rasmlari**: hozircha 📦 belgisi qo'yilgan — `image_url` maydoniga rasm havolasini yozib, `web/index.html` dagi `.card-img` qismini `<img>` ga almashtirsangiz bo'ldi.

## To'lov tizimlarini ulash (Click / Payme)

Hozircha `payments/click.py` va `payments/payme.py` — ishlaydigan **skelet/stub** kod
(checkout havolasi yaratish, imzo tekshirish, webhook formatlari tayyor).
Real ishlashi uchun:

1. `https://merchant.click.uz` va `https://business.payme.uz` da ro'yxatdan o'ting.
2. Merchant ID, Service ID va maxfiy kalitlarni oling.
3. `.env` fayliga joylashtiring.
4. `backend/routers/` ichiga `payments.py` router qo'shib, Click/Payme webhooklarini
   (`handle_prepare`, `handle_complete` va h.k.) API endpoint sifatida ulang — bu
   funksiyalarning skeleti tayyor, faqat DB bilan bog'lash qoladi.

## Railway'ga joylashtirish

Railway'da repository'dan ikkita service yarating:

1. `zoopet-web` — repository root'dagi `railway.toml` ishlatiladi.
2. `zoopet-bot` — service settings'da Config File Path sifatida `railway.bot.toml` ni tanlang.

`zoopet-web` uchun Railway PostgreSQL service ulang va quyidagi environment qiymatlarni kiriting:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
BOT_TOKEN
JWT_SECRET
ADMIN_CHAT_ID
MINIAPP_URL=https://zoopet-web-production.up.railway.app/
CLOUDINARY_CLOUD_NAME
CLOUDINARY_API_KEY
CLOUDINARY_API_SECRET
```

Railway PostgreSQL URL'i `postgresql://` ko'rinishida berilsa ham, ilova uni psycopg uchun
`postgresql+psycopg://` formatiga avtomatik moslaydi.

Migrationni web service deployidan oldin bir marta ishga tushiring:

```bash
alembic upgrade head
```

Mavjud SQLite ma'lumotlarini PostgreSQL'ga local kompyuterdan import qiling:

```bash
python -m backend.migrate_sqlite --source backend/zoopet.db --dry-run
python -m backend.migrate_sqlite --source backend/zoopet.db
python -m backend.create_admin
```

`zoopet-bot` service uchun `BOT_TOKEN` va `MINIAPP_URL` yetarli. Telegram polling sababli bot
service'ni bitta replica bilan qoldiring va BotFather'da ham shu HTTPS URL'ni Mini App URL sifatida kiriting.

## Keyingi qadamlar (production uchun tavsiyalar)

- SQLite o'rniga PostgreSQL'ga o'tish (yuqori yuklama uchun).
- Rasmlarni saqlash uchun S3/Cloudinary kabi xizmat ulash.
- Serverni Railway.app yoki VPS'ga joylashtirish.
- HTTPS va domain sozlash.
- Mobil ilova (Android/iOS) uchun bu API'dan foydalanib React Native yoki Flutter'da
  native ilova yaratish mumkin — API tayyor, faqat frontendni qo'shish kerak.
