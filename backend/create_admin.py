"""
Admin hisobini yaratish / parolini almashtirish uchun CLI.

Avval buni ochiq `POST /api/admin/seed-default` endpointi bajarardi — u
autentifikatsiyasiz ishlab, `admin` / `admin123` yaratar va parolni javob
tanasida qaytarardi. Endi parol faqat shu skript orqali, terminaldan
kiritiladi va hech qachon tarmoq orqali uzatilmaydi.

Ishlatish:
    python -m backend.create_admin              # interaktiv
    python -m backend.create_admin --username admin
"""
import argparse
import getpass
import sys

from dotenv import load_dotenv

load_dotenv()

from .database import SessionLocal
from . import models
from . import customer_auth

MIN_PASSWORD_LENGTH = 10


def _prompt_password() -> str:
    while True:
        password = getpass.getpass("Yangi parol: ")
        if len(password) < MIN_PASSWORD_LENGTH:
            print(f"❌ Parol kamida {MIN_PASSWORD_LENGTH} ta belgidan iborat bo'lishi kerak.")
            continue
        if password != getpass.getpass("Parolni tasdiqlang: "):
            print("❌ Parollar mos kelmadi.")
            continue
        return password


def main() -> int:
    parser = argparse.ArgumentParser(description="ZooPet admin hisobini yaratish yoki parolini almashtirish")
    parser.add_argument("--username", help="Admin login (so'ralmasa: admin)")
    args = parser.parse_args()

    username = args.username or input("Admin login [admin]: ").strip() or "admin"

    db = SessionLocal()
    try:
        admin = db.query(models.Admin).filter(models.Admin.username == username).first()
        if admin:
            print(f"ℹ️  '{username}' allaqachon mavjud — paroli almashtiriladi.")
        else:
            print(f"➕ Yangi admin yaratiladi: '{username}'")

        password = _prompt_password()
        password_hash = customer_auth.hash_password(password)

        if admin:
            admin.password_hash = password_hash
        else:
            db.add(models.Admin(username=username, password_hash=password_hash))
        db.commit()
    finally:
        db.close()

    print(f"✅ Tayyor. Admin panelga '{username}' bilan kirishingiz mumkin: /admin/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
