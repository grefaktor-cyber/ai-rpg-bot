import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                           CallbackQuery, LabeledPrice)
from aiogram.enums import ParseMode

from db import DB
import ai

# === НАСТРОЙКИ ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
GIGACHAT_CREDENTIALS = os.environ.get("GIGACHAT_CREDENTIALS", "")
FREE_DAILY_LIMIT = 10
PREMIUM_PRICE_STARS = 100
AI_MARKER = "🤖 Сгенерировано ИИ"
# =================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = DB()

CONSENT_TEXT = (
    "📋 <b>Перед началом — важное</b>\n\n"
    "Бот обрабатывает ваши персональные данные (Telegram ID, username) "
    "для сохранения игрового прогресса.\n\n"
    "• Данные хранятся на сервере.\n"
    "• Весь контент сгенерирован ИИ и маркируется.\n"
    "• Игра предназначена для лиц <b>18+</b>.\n"
    "• Вы можете отозвать согласие командой /revoke.\n\n"
    "Нажимая «Согласен», вы подтверждаете согласие на обработку ПДн "
    "и что вам исполнилось 18 лет."
)


@dp.message(Command("start"))
async def start(m: Message):
    args = m.text.split()
    referrer_id = 0
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
        except ValueError:
            pass

    user = db.get_user(m.from_user.id, m.from_user.username or "")

    if referrer_id and user["referred_by"] == 0:
        if db.set_referrer(m.from_user.id, referrer_id):
            await m.answer("🎉 Вы пришли по приглашению! Ваш друг получил +10 действий.")

    if user["consent_given"]:
        me = await bot.get_me()
        ref_link = f"https://t.me/{me.username}?start=ref_{m.from_user.id}"
        await m.answer(
            f"🎮 С возвращением!\n\n"
            f"🔗 Ваша реферальная ссылка: {ref_link}\n"
            f"👥 Приглашено друзей: {user['referral_count']}\n"
            f"За каждого друга — +10 действий!"
        )
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Согласен (18+)", callback_data="consent_yes"),
        InlineKeyboardButton(text="❌ Отказаться", callback_data="consent_no"),
    ]])
    await m.answer(CONSENT_TEXT, reply_markup=kb, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "consent_yes")
async def consent_yes(c: CallbackQuery):
    db.give_consent(c.from_user.id)
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{c.from_user.id}"
    await c.message.edit_text(
        "✅ Согласие получено. Добро пожаловать в <b>AI-Приключение</b>!\n\n"
        "Просто пиши, что делает герой:\n"
        "• «Я осматриваюсь»\n• «Иду в таверну»\n• «Атакую гоблина»\n\n"
        f"📊 Бесплатно: {FREE_DAILY_LIMIT} действий в день.\n"
        f"🔗 Твоя ссылка для друзей: {ref_link}\n"
        f"За каждого друга — +10 действий!\n\n"
        f"💎 Безлимит → /buy\n"
        f"{AI_MARKER}",
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data == "consent_no")
async def consent_no(c: CallbackQuery):
    await c.message.edit_text(
        "❌ Без согласия на обработку данных бот не может сохранять прогресс. "
        "Вы можете вернуться в любой момент командой /start."
    )


@dp.message(Command("revoke"))
async def revoke(m: Message):
    db.revoke_consent(m.from_user.id)
    await m.answer("🗑 Согласие отозвано, история удалена. Вернуться — /start.")


@dp.message(Command("reset"))
async def reset(m: Message):
    db.update_story(m.from_user.id, "")
    await m.answer("🔄 История сброшена.")


@dp.message(Command("premium"))
async def premium(m: Message):
    await m.answer(
        "💎 <b>Премиум</b>\n\n• Безлимитные действия\n"
        "• Приоритетная обработка\n\n"
        "Купить → /buy",
        parse_mode=ParseMode.HTML
    )


@dp.message(Command("buy"))
async def buy(m: Message):
    await bot.send_invoice(
        chat_id=m.chat.id,
        title="Премиум-подписка AI-Приключение",
        description="Безлимитные действия, приоритетная обработка",
        payload="premium_30d",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Премиум на 30 дней", amount=PREMIUM_PRICE_STARS)],
        start_parameter="premium"
    )


@dp.pre_checkout_query()
async def pre_checkout(q):
    await q.answer(ok=True)


@dp.message(F.successful_payment)
async def on_payment(m: Message):
    db.set_premium(m.from_user.id, 1)
    await m.answer(
        "💎 <b>Оплата получена!</b>\n\n"
        "Премиум активирован на 30 дней.\n"
        "Приятной игры!",
        parse_mode=ParseMode.HTML
    )


@dp.message(F.text)
async def handle(m: Message):
    uid = m.from_user.id
    user = db.get_user(uid, m.from_user.username or "")

    if not user["consent_given"]:
        await m.answer("⚠️ Сначала примите условия: /start")
        return

    if not user["is_premium"] and user["requests_today"] >= FREE_DAILY_LIMIT:
        await m.answer(
            f"⏳ Лимит на сегодня исчерпан ({FREE_DAILY_LIMIT} действий).\n\n"
            "💎 Премиум без лимитов → /buy\n"
            "Или пригласи друга → +10 действий!"
        )
        return

    await bot.send_chat_action(m.chat.id, "typing")
    action = m.text.strip()[:500]
    response = await ai.generate(GIGACHAT_AUTH_KEY, user["story"], action)

    new_story = (user["story"] + f"\nИГРОК: {action}\nМАСТЕР: {response}")[-4000:]
    db.update_story(uid, new_story)
    db.increment(uid)

    left = "∞" if user["is_premium"] else FREE_DAILY_LIMIT - user["requests_today"] - 1
    await m.answer(
        f"{response}\n\n<i>{AI_MARKER} · Осталось: {left}</i>",
        parse_mode=ParseMode.HTML
    )


# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def handle_health(request):
    return web.Response(text="Bot is running")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"✅ Веб-сервер запущен на порту {port}")


async def main():
    await start_web_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())