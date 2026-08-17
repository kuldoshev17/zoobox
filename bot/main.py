"""
ZooPet Telegram bot — Mini App uchun yupqa ishga tushiruvchi.

Butun do'kon (katalog, savat, buyurtma, buyurtmalar tarixi) endi faqat
Telegram Mini App ichida ishlaydi (web/index.html). Bot hech qanday
backend API'ga murojaat qilmaydi — u faqat Mini App'ni ochish tugmasini
ko'rsatadi.

Ishga tushirish:
    1. .env faylida BOT_TOKEN va MINIAPP_URL ni sozlang
    2. python -m bot.main
"""
import os
import sys
import logging

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()  # .env dagi BOT_TOKEN va MINIAPP_URL ni yuklash

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
# Telegram Mini App uchun ochiq HTTPS manzil (masalan ngrok yoki production domen).
MINIAPP_URL = os.getenv("MINIAPP_URL", "")

START_TEXT = {
    "uz": (
        "🐾 *ZooPet* ga xush kelibsiz!\n\n"
        "Uy hayvonlaringiz uchun kerakli mahsulotlarni tanlang va biz uni "
        "eshigingizgacha yetkazib beramiz.\n\n"
        "Do'konni ochish uchun quyidagi tugmani bosing:"
    ),
    "ru": (
        "🐾 Добро пожаловать в *ZooPet*!\n\n"
        "Выберите нужные товары для питомца, а мы доставим их прямо к двери.\n\n"
        "Нажмите кнопку ниже, чтобы открыть магазин:"
    ),
}
BUTTON_LABEL = {"uz": "🛒 Do'konni ochish", "ru": "🛒 Открыть магазин"}
MENU_BUTTON_LABEL = {"uz": "Do'kon", "ru": "Магазин"}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = "ru" if (update.effective_user.language_code or "").lower().startswith("ru") else "uz"
    text = START_TEXT.get(lang, START_TEXT["uz"])
    button_label = BUTTON_LABEL.get(lang, BUTTON_LABEL["uz"])
    menu_label = MENU_BUTTON_LABEL.get(lang, MENU_BUTTON_LABEL["uz"])

    keyboard = []
    if MINIAPP_URL:
        keyboard.append(
            [InlineKeyboardButton(button_label, web_app=WebAppInfo(url=MINIAPP_URL))]
        )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
    )

    if MINIAPP_URL:
        await context.bot.set_chat_menu_button(
            chat_id=update.effective_chat.id,
            menu_button=MenuButtonWebApp(text=menu_label, web_app=WebAppInfo(url=MINIAPP_URL))
        )


async def _setup_menu_button(app: Application) -> None:
    """Mini App mavjud bo'lsa, xabar maydoni yonidagi doimiy menyu tugmasini sozlaydi."""
    if MINIAPP_URL:
        await app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text=MENU_BUTTON_LABEL["uz"], web_app=WebAppInfo(url=MINIAPP_URL))
        )


def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️  BOT_TOKEN muhit o'zgaruvchisi sozlanmagan. .env faylini tekshiring.")
    if not MINIAPP_URL:
        print("⚠️  MINIAPP_URL sozlanmagan — bot /start buyrug'iga hech qanday amal qila olmaydi.")

    app = Application.builder().token(BOT_TOKEN).post_init(_setup_menu_button).build()
    app.add_handler(CommandHandler("start", start))

    print("🐾 ZooPet bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
