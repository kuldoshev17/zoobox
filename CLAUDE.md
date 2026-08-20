# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ZooPet — a pet-supplies delivery platform for the Uzbek market (Zoo Planeta-style, original code). One FastAPI backend serves a Telegram Mini App storefront (the only way customers shop — see Architecture) and a separate vanilla-JS admin panel; a thin Telegram bot just launches the Mini App. All UI text and code comments are in Uzbek.

## Commands

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell/cmd); use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env                          # fill in BOT_TOKEN, MINIAPP_URL, JWT_SECRET, ADMIN_CHAT_ID, payment keys

python -m backend.seed                        # one-time: seed categories/products (skips if data exists)
uvicorn backend.main:app --reload --port 8000 # run API + storefront + admin panel

curl -X POST http://127.0.0.1:8000/api/admin/seed-default  # create default admin (admin/admin123), once

python -m bot.main                            # run Telegram bot (needs backend running, separate terminal)

# Render deployment (Blueprint: render.yaml)
alembic upgrade head                            # run as the web service pre-deploy command
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
python -m bot.main                              # single background worker instance
```

There is no test suite, linter, or build step configured in this repo.

- Storefront: `http://127.0.0.1:8000/`
- Admin panel: `http://127.0.0.1:8000/admin/`
- API: `http://127.0.0.1:8000/api/...`
- Requires Python 3.9+ (code intentionally avoids PEP 604 `X | None` union syntax and uses `typing.Optional` instead, for compatibility with older interpreters).
- Render uses one web service (`uvicorn backend.main:app --host 0.0.0.0 --port $PORT`), one single-instance bot worker (`python -m bot.main`), and Render PostgreSQL. The web service runs `alembic upgrade head` as its pre-deploy command; do not run multiple polling workers.
- Render's filesystem is ephemeral. Product uploads use Cloudinary when `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` are configured; local development falls back to `backend/uploads`.
- `backend/main.py` and `bot/main.py` call `load_dotenv()` at the top before reading any `os.getenv(...)`, so `.env` is picked up automatically — no need to `export`/`set` vars manually.
- PostgreSQL production uses Alembic migrations in `migrations/`; run `alembic upgrade head` before starting the app. `backend/main.py` does not create tables at import time. Local development keeps SQLite as the fallback when `DATABASE_URL` is unset, and `backend.seed` creates missing SQLite tables in that mode.
- To preserve an existing SQLite database during cutover, set PostgreSQL `DATABASE_URL`, run `python -m backend.migrate_sqlite --source backend/zoopet.db --dry-run`, then run it without `--dry-run`. The importer is non-destructive and creates a `.migration-backup` copy.

## Architecture

**Single FastAPI app serves everything.** `backend/main.py` creates DB tables on import, mounts the `catalog`, `orders`, `admin_auth`, `customer_auth`, and `subscriptions` routers under `/api`, then mounts `web/` as static files at `/` (catch-all, must stay registered last). There is no separate frontend build — `web/index.html` and `web/admin/index.html` are self-contained HTML/CSS/JS files that call the `/api/*` endpoints directly with `fetch`.

**Data layer**: SQLAlchemy models in `backend/models.py`, SQLite at `backend/zoopet.db` (created automatically, path in `backend/database.py`). Core entities: `Category` → `Product`, `Customer` → `Order` → `OrderItem`, plus `Admin`. `Order`/`OrderItem` snapshot `product_name`/`unit_price` at creation time so historical orders don't change if a product is later edited or deactivated. `Customer` is now a real account (`telegram_id`/`phone`/`full_name`/`password_hash` all `nullable=False`) — every row exists because someone completed registration, there is no more guest/anonymous customer.

**Request/response validation**: Pydantic schemas in `backend/schemas.py`, kept separate from the SQLAlchemy models (`*Out` schemas use `from_attributes = True` to serialize ORM objects).

**The storefront is a Telegram Mini App only — there is no plain-browser/guest path.** `web/index.html` is the entire shopping experience (catalog, cart, checkout, order history) and assumes it is always opened inside Telegram's WebView; if `window.Telegram.WebApp` is absent it shows a static "open via the bot" message and does nothing else. `bot/main.py` is a thin launcher — `/start` shows a `WebAppInfo` inline button and (via `_setup_menu_button()`/`post_init`) sets the persistent chat menu button; the bot makes no backend HTTP calls at all and holds no cart/order state.

**Customer auth is the stronger precedent in this codebase now** (`backend/customer_auth.py` + `backend/routers/customer_auth.py`) — bcrypt password hashing and `PyJWT` session tokens (30-day expiry, `JWT_SECRET` env var), unlike `admin_auth.py`'s deliberately minimal SHA-256/in-memory-token scheme (still fine for the admin panel, but don't copy it for anything customer-facing). Flow: `POST /api/customer/register` requires a verified Telegram `initData` (via `telegram_auth.get_telegram_user`) plus phone/password/full_name, binding `Customer.telegram_id` trustworthily at account-creation time; `GET /api/customer/me` is the auto-recognition endpoint the Mini App calls on every load — tries a stored `Authorization: Bearer <jwt>` first, falls back to `Authorization: tma <initData>` for a fresh-but-tokenless visit (200 + re-issued token if that `telegram_id` is already registered, 404 if not — the client's cue to show the registration form); `POST /api/customer/login` (phone+password, no Telegram needed) exists as an escape hatch for the rare case `/me`'s `telegram_id` lookup can't resolve (dev-db reset, corrupted row). `GET /api/customer/orders` returns the authenticated customer's own order history/status. `POST /api/orders` requires a valid Bearer token (`customer_auth.get_current_customer`) — no more optional/guest path; `delivery_phone`/`customer_id` come from the authenticated `Customer`, not the request body.

**`backend/telegram_auth.py`** now only backs registration/auto-recognition (`verify_init_data`/`get_telegram_user`), not order creation directly — moving order auth off raw `initData` (which expires after 5 minutes, `max_age=300`) and onto a long-lived JWT fixed a real bug where a Mini App left open past that window would fail checkout with a stale-signature error.

**Profile editing**: `PATCH /api/customer/me` (`backend/routers/customer_auth.py`) updates `full_name` freely, but changing `password_hash` requires the correct `current_password` even though the Mini App's normal flow never re-asks for it after registration — a stolen/leaked JWT alone shouldn't be able to permanently lock the real owner out by silently changing their password.

**Optional subscription plans** (`backend/routers/subscriptions.py`, models `SubscriptionPlan`/`Subscription` in `models.py`) — an entirely separate, optional path alongside normal product ordering; selecting a plan never gates or is gated by cart checkout. `SubscriptionPlan` rows are scoped per `(tier, species)` (EKO/BASIC/PLUS/PREMIUM × cat/dog, seeded in `backend/seed.py` — note dogs have no EKO tier, matching the source pricing doc which never gave one). A customer can hold only one `ACTIVE` subscription at a time (enforced in the router, not a DB constraint, so cancelled history is kept — `POST /api/customer/subscription` 409s if one is already active); cancelling is a soft status flip (`CANCELLED` + `cancelled_at`), same idiom as `Product.is_active`. **There is no recurring/automated billing** — selecting a plan just creates the `Subscription` record and notifies admins (`notify_admin_new_subscription`, same fire-and-forget shape as `notify_admin_new_order`); actual monthly billing/fulfillment is arranged manually by the business, since neither `payments/click.py` nor `payments/payme.py` support recurring/tokenized charges (both are one-shot checkout-link stubs — confirmed by reading both in full). The admin panel's "Obunalar" tab is read-only visibility (`GET /api/admin/subscriptions`, unauthenticated like `GET /api/orders` today — a pre-existing gap, not introduced here); plan CRUD isn't built yet, adjust `SubscriptionPlan` rows directly in the DB or `seed.py` for now.

**Two distinct, easily-confused Mini App launch surfaces**: (1) `bot/main.py`'s `_setup_menu_button()` calls `Bot.set_chat_menu_button(MenuButtonWebApp(...))` — this only controls the small icon next to the message compose box *inside an open chat*. (2) The "Open" pill button on the bot's *chat-list row* (shown before the chat is even opened, e.g. like official bots such as Wallet) is a **separate, manual, code-independent setting** in BotFather: `/mybots` → select bot → *Bot Settings* → *Configure Mini App* → *Enable Mini App*, pasting the same Mini App URL. There is no Bot API call for this second one — it can't be automated from `bot/main.py`. Telegram clients cache this setting, so a restart of the Telegram app (or refresh of the web client) is often needed before it appears.

**Payments** (`payments/click.py`, `payments/payme.py`) are stubs/skeletons, not wired into any router yet — `generate_pay_link`, `verify_signature`/`verify_auth`, and the `handle_*` webhook functions are implemented per each provider's docs but return placeholder data and don't touch the DB. Wiring them up means adding a `backend/routers/payments.py` that calls into these modules and updates `Order.payment_status`.

## Conventions

- New API endpoints go in `backend/routers/`, each with its own `APIRouter(prefix="/api/...")`, registered in `backend/main.py`.
- Enums (`OrderStatus`, `PaymentMethod`, `PaymentStatus` in `models.py`) are the source of truth for valid string values — validate incoming strings against `[s.value for s in models.SomeEnum]` rather than hardcoding lists (see `update_order_status`).
- Money is stored/passed as so'm floats (no cents/tiyin) except in the Payme integration, which converts to tiyin (`amount * 100`) only at the point of building the checkout link.
