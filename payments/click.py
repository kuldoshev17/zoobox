"""
CLICK to'lov tizimi integratsiyasi (STUB).

Bu yerda Click Merchant API bilan ishlash uchun asosiy skelet keltirilgan.
Ishga tushirish uchun quyidagilarni https://merchant.click.uz dan olib,
.env fayliga qo'shishingiz kerak:

    CLICK_MERCHANT_ID=...
    CLICK_SERVICE_ID=...
    CLICK_SECRET_KEY=...
    CLICK_MERCHANT_USER_ID=...

Click ishlash tartibi (umumiy oqim):
1. Foydalanuvchi checkout paytida "Click orqali to'lash" tugmasini bosadi.
2. Backend generate_pay_link() orqali to'lov havolasini yaratadi va foydalanuvchini
   shu havolaga yo'naltiradi (yoki Telegram botda inline tugma sifatida yuboradi).
3. Click server "Prepare" so'rovini yuboradi -> handle_prepare()
4. To'lov muvaffaqiyatli bo'lsa, Click "Complete" so'rovini yuboradi -> handle_complete()
5. Complete bosqichida order.payment_status = PAID qilib belgilanadi.

DIQQAT: Bu real ishlaydigan integratsiya emas - signature tekshiruvi va
haqiqiy API chaqiruvlari uchun Click hujjatlariga asosan to'ldirilishi kerak:
https://docs.click.uz
"""
import hashlib
import os
import time
from typing import Optional

CLICK_MERCHANT_ID = os.getenv("CLICK_MERCHANT_ID", "")
CLICK_SERVICE_ID = os.getenv("CLICK_SERVICE_ID", "")
CLICK_SECRET_KEY = os.getenv("CLICK_SECRET_KEY", "")
CLICK_MERCHANT_USER_ID = os.getenv("CLICK_MERCHANT_USER_ID", "")

CLICK_CHECKOUT_URL = "https://my.click.uz/services/pay"


def generate_pay_link(order_id: int, amount: float, return_url: str = "") -> str:
    """
    Click checkout sahifasiga yo'naltiruvchi havola yaratadi.
    Merchant ID va Service ID .env orqali sozlanishi kerak.
    """
    if not CLICK_MERCHANT_ID or not CLICK_SERVICE_ID:
        return "#click-not-configured"

    params = (
        f"?service_id={CLICK_SERVICE_ID}"
        f"&merchant_id={CLICK_MERCHANT_ID}"
        f"&amount={amount}"
        f"&transaction_param={order_id}"
    )
    if return_url:
        params += f"&return_url={return_url}"
    return CLICK_CHECKOUT_URL + params


def verify_signature(data: dict) -> bool:
    """
    Click'dan kelgan so'rovning sign_string maydonini tekshiradi.
    Click hujjatidagi md5 formulasi asosida to'ldirilishi kerak.
    """
    if not CLICK_SECRET_KEY:
        return False
    # Click MD5 formulasi (namuna, hujjat bo'yicha aniqlashtiring):
    # md5(click_trans_id + service_id + SECRET_KEY + merchant_trans_id + amount + action + sign_time)
    raw = (
        f"{data.get('click_trans_id','')}{data.get('service_id','')}"
        f"{CLICK_SECRET_KEY}{data.get('merchant_trans_id','')}"
        f"{data.get('amount','')}{data.get('action','')}{data.get('sign_time','')}"
    )
    expected = hashlib.md5(raw.encode()).hexdigest()
    return expected == data.get("sign_string")


def handle_prepare(data: dict) -> dict:
    """Click 'Prepare' bosqichi uchun javob (real integratsiyada DBga yozing)."""
    return {
        "click_trans_id": data.get("click_trans_id"),
        "merchant_trans_id": data.get("merchant_trans_id"),
        "merchant_prepare_id": int(time.time()),
        "error": 0,
        "error_note": "Success",
    }


def handle_complete(data: dict) -> dict:
    """Click 'Complete' bosqichi - shu yerda order.payment_status = PAID qilinadi."""
    return {
        "click_trans_id": data.get("click_trans_id"),
        "merchant_trans_id": data.get("merchant_trans_id"),
        "merchant_confirm_id": int(time.time()),
        "error": 0,
        "error_note": "Success",
    }
