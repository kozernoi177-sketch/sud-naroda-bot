from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import random
import asyncio

from config import BOT_TOKEN
from db import *
from economy import calculate_level
from texts import TEXTS

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

init_db()

# =========================
# ГЛОБАЛЬНОЕ СОСТОЯНИЕ
# =========================

game_active = False
game_chat_id = None
players = []
roles = {}
votes = {}

current_accused = None
truth = None
round_number = 0
max_rounds = 3

lawyer_used = False
prosecutor_used = False
detective_used = False


# =========================
# ВСПОМОГАТЕЛЬНОЕ
# =========================

def get_lang(user_id):
    user = get_user(user_id)
    if user:
        return user[2]
    return "ru"


def main_menu(bot_username):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("⚖️ Создать игру", callback_data="create_game"),
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("🎭 Роли", callback_data="roles_menu"),
        InlineKeyboardButton("📜 Об игре", callback_data="about_game"),
        InlineKeyboardButton("🌍 Язык", callback_data="language"),
        InlineKeyboardButton(
            "➕ Добавить в чат",
            url=f"https://t.me/{bot_username}?startgroup=true"
        )
    )
    return kb


# =========================
# START
# =========================

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    register_user(message.from_user.id, message.from_user.username)
    bot_info = await bot.get_me()

    text = (
        "⚖️ <b>СУД НАРОДА</b>\n\n"
        "🎭 Психологическая игра голосования\n"
        "💰 Прокачивайся. Побеждай.\n"
        "🏆 Докажи, что чувствуешь истину.\n\n"
        "Выберите действие:"
    )

    await message.answer(
        text,
        reply_markup=main_menu(bot_info.username),
        parse_mode="HTML"
    )


# =========================
# ПРОФИЛЬ
# =========================

@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    level = calculate_level(user[5])

    text = (
        "👤 <b>ПРОФИЛЬ</b>\n\n"
        f"🧑 Ник: @{user[1]}\n\n"
        f"💵 Баланс: <b>{user[3]}</b>\n"
        f"⭐ Уровень: <b>{level}</b>\n"
        f"🏆 Победы: <b>{user[6]}</b>\n"
        f"🎮 Игр сыграно: <b>{user[7]}</b>\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("⬅ Назад", callback_data="back")
        ),
        parse_mode="HTML"
    )
    await callback.answer()


# =========================
# ОБ ИГРЕ
# =========================

@dp.callback_query_handler(lambda c: c.data == "about_game")
async def about_game(callback: types.CallbackQuery):

    text = (
        "📜 <b>КАК ПРОХОДИТ ИГРА</b>\n\n"
        "1️⃣ Каждый раунд выбирается обвиняемый.\n"
        "2️⃣ Система знает истину.\n"
        "3️⃣ Игроки голосуют.\n"
        "4️⃣ Спец-роли влияют на исход.\n\n"
        "🎯 Голосуй правильно.\n"
        "💰 Получай награды.\n"
        "🏆 Побеждай."
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("⬅ Назад", callback_data="back")
        ),
        parse_mode="HTML"
    )
    await callback.answer()


# =========================
# РОЛИ (POPUP STYLE)
# =========================

@dp.callback_query_handler(lambda c: c.data == "roles_menu")
async def roles_menu(callback: types.CallbackQuery):

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🕵 Детектив", callback_data="role_detective"),
        InlineKeyboardButton("⚖ Судья", callback_data="role_judge"),
        InlineKeyboardButton("🎯 Прокурор", callback_data="role_prosecutor"),
        InlineKeyboardButton("🛡 Адвокат", callback_data="role_lawyer"),
        InlineKeyboardButton("🧨 Мститель", callback_data="role_avenger"),
        InlineKeyboardButton("👤 Гражданин", callback_data="role_citizen"),
        InlineKeyboardButton("⬅ Назад", callback_data="back")
    )

    await callback.message.edit_text("🎭 Выберите роль:", reply_markup=kb)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("role_"))
async def role_info(callback: types.CallbackQuery):

    role = callback.data.split("_")[1]

    descriptions = {
        "detective": "🕵 Детектив\n\n/check — узнать истину (1 раз).",
        "judge": "⚖ Судья\n\nЕго голос считается за 2.",
        "prosecutor": "🎯 Прокурор\n\n/accuse — сменить обвиняемого (1 раз).",
        "lawyer": "🛡 Адвокат\n\n/protect — убрать 1 голос (1 раз).",
        "avenger": "🧨 Мститель\n\n/revenge @ник — если казнили, забирает игрока.",
        "citizen": "👤 Гражданин\n\nПросто голосует."
    }

    await callback.message.edit_text(
        descriptions[role],
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("⬅ Назад", callback_data="roles_menu")
        )
    )
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    bot_info = await bot.get_me()

    text = (
        "⚖️ <b>СУД НАРОДА</b>\n\n"
        "🎭 Психологическая игра голосования\n"
        "💰 Прокачивайся. Побеждай.\n"
        "🏆 Докажи, что чувствуешь истину.\n\n"
        "Выберите действие:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=main_menu(bot_info.username),
        parse_mode="HTML"
    )
    await callback.answer()


# =========================
# ИГРА
# =========================

@dp.callback_query_handler(lambda c: c.data == "create_game")
async def create_game(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Добавьте бота в группу и напишите /join",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("⬅ Назад", callback_data="back")
        )
    )
    await callback.answer()


@dp.message_handler(commands=['join'])
async def join(message: types.Message):
    global game_active, game_chat_id

    if message.chat.type == "private":
        return

    if game_active:
        await message.answer("Игра уже идёт.")
        return

    if message.from_user.id not in players:
        players.append(message.from_user.id)
        game_chat_id = message.chat.id
        await message.answer(f"Игроков: {len(players)}")

        if len(players) >= 4:
            await start_game()


async def start_game():
    global game_active, roles, round_number

    game_active = True
    round_number = 0
    roles.clear()

    shuffled = players.copy()
    random.shuffle(shuffled)

    roles[shuffled[0]] = "detective"
    roles[shuffled[1]] = "judge"
    roles[shuffled[2]] = "prosecutor"

    if len(players) >= 6:
        roles[shuffled[3]] = "lawyer"
        roles[shuffled[4]] = "avenger"

    for p in players:
        if p not in roles:
            roles[p] = "citizen"

    for uid, role in roles.items():
        try:
            await bot.send_message(uid, f"🎭 Ваша роль: {role}")
        except:
            pass

    await start_round()


async def start_round():
    global round_number, current_accused, truth, votes
    global lawyer_used, prosecutor_used, detective_used

    votes.clear()
    lawyer_used = False
    prosecutor_used = False
    detective_used = False

    round_number += 1

    current_accused = random.choice(players)
    truth = random.choice(["guilty", "innocent"])

    user = await bot.get_chat(current_accused)

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔴 Казнить", callback_data="guilty"),
        InlineKeyboardButton("🟢 Оправдать", callback_data="innocent")
    )

    await bot.send_message(
        game_chat_id,
        f"⚖️ <b>РАУНД {round_number}/{max_rounds}</b>\n\n"
        f"👤 Обвиняемый: @{user.username if user.username else user.first_name}",
        reply_markup=kb,
        parse_mode="HTML"
    )

    await asyncio.sleep(20)
    await finish_round()


@dp.callback_query_handler(lambda c: c.data in ["guilty", "innocent"])
async def vote(callback: types.CallbackQuery):
    votes[callback.from_user.id] = callback.data
    await callback.answer("Голос принят")


async def finish_round():
    global game_active

    guilty = 0
    innocent = 0

    for uid, vote in votes.items():
        mult = 2 if roles.get(uid) == "judge" else 1
        if vote == "guilty":
            guilty += mult
        elif vote == "innocent":
            innocent += mult

    result = "guilty" if guilty > innocent else "innocent"

    for p in players:
        add_game(p)
        update_money(p, 20)
        update_exp(p, 30)

    if result == truth:
        for uid, vote in votes.items():
            if vote == truth:
                add_win(uid)
                update_money(uid, 30)

    if round_number < max_rounds:
        await start_round()
    else:
        game_active = False
        players.clear()
        await bot.send_message(
            game_chat_id,
            "🏆 <b>СУД ЗАВЕРШЁН</b>\n\nИстина раскрыта.",
            parse_mode="HTML"
        )


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
