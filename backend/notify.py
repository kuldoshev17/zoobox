"""
Admin(lar)ga yangi buyurtma haqida Telegram orqali xabar yuborish.
Bot tokeni va admin chat_id .env orqali sozlanadi:

    BOT_TOKEN=...
    ADMIN_CHAT_ID=...   (bir nechta bo'lsa vergul bilan ajrating: 111,222)
"""
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_IDS = [c.strip() for c in os.getenv("ADMIN_CHAT_ID", "").split(",") if c.strip()]


def notify_admin_new_order(order) -> None:
    if not BOT_TOKEN or not ADMIN_CHAT_IDS:
        return  # sozlanmagan bo'lsa jim o'tkazib yuboramiz

    lines = [f"🆕 Yangi buyurtma #{order.id}"]
    for item in order.items:
        lines.append(f"• {item.product_name} x{item.quantity} = {item.unit_price * item.quantity:,.0f} so'm")
    lines.append(f"\n📦 Yetkazib berish: {order.delivery_fee:,.0f} so'm")
    lines.append(f"💰 Jami: {order.total_amount:,.0f} so'm")
    lines.append(f"💳 To'lov: {order.payment_method}")
    lines.append(f"📍 Manzil: {order.delivery_address}")
    lines.append(f"📞 Tel: {order.delivery_phone}")
    if order.comment:
        lines.append(f"💬 Izoh: {order.comment}")
    text = "\n".join(lines)

    for chat_id in ADMIN_CHAT_IDS:
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=5,
            )
        except requests.RequestException:
            pass  # xabar yetmasa ham buyurtma yaratilishiga to'sqinlik qilmasin


def notify_admin_new_subscription(subscription) -> None:
    if not BOT_TOKEN or not ADMIN_CHAT_IDS:
        return  # sozlanmagan bo'lsa jim o'tkazib yuboramiz

    plan = subscription.plan
    customer = subscription.customer
    text = (
        f"🔁 Yangi obuna #{subscription.id}\n"
        f"Tarif: {plan.name} ({plan.species.value})\n"
        f"Narx: {plan.price:,.0f} so'm/oy\n"
        f"Mijoz: {customer.full_name}\n"
        f"📞 Tel: {customer.phone}"
    )

    for chat_id in ADMIN_CHAT_IDS:
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=5,
            )
        except requests.RequestException:
            pass  # xabar yetmasa ham obuna yaratilishiga to'sqinlik qilmasin
