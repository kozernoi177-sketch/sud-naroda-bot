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

# =======================
# ГЛОБАЛЬНОЕ СОСТОЯНИЕ ИГРЫ
# =======================

game_active = False
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
revenge_pending = False
avenger_id = None


# =======================
# ВСПОМОГАТЕЛЬНОЕ
# =======================

def get_lang(user_id):
    user = get_user(user_id)
    if user:
        return user[2]
    return "ru"


# =======================
# START
# =======================

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    register_user(message.from_user.id, message.from_user.username)
    lang = get_lang(message.from_user.id)

    bot_info = await bot.get_me()

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("⚖️ Создать игру", callback_data="create_game"),
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("🎭 Роли", callback_data="roles_menu"),
        InlineKeyboardButton("🌍 Язык", callback_data="language"),
        InlineKeyboardButton(
            "➕ Добавить в группу",
            url=f"https://t.me/{bot_info.username}?startgroup=true"
        )
    )

    await message.answer(TEXTS[lang]["welcome"], reply_markup=keyboard)


# =======================
# ПРОФИЛЬ
# =======================

@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    level = calculate_level(user[5])

    text = (
        f"👤 @{user[1]}\n\n"
        f"💵 Деньги: {user[3]}\n"
        f"💎 Камни: {user[4]}\n"
        f"⭐ Уровень: {level}\n"
        f"🏆 Победы: {user[6]}\n"
        f"🎮 Игр сыграно: {user[7]}"
    )

    await callback.message.answer(text)
    await callback.answer()


# =======================
# ЯЗЫК
# =======================

@dp.callback_query_handler(lambda c: c.data == "language")
async def language(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
    )
    await callback.message.answer("Выберите язык:", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    update_language(callback.from_user.id, lang)
    await callback.message.answer("✅ Language updated.")
    await callback.answer()


# =======================
# МЕНЮ РОЛЕЙ
# =======================

@dp.callback_query_handler(lambda c: c.data == "roles_menu")
async def roles_menu(callback: types.CallbackQuery):

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🕵 Детектив", callback_data="role_detective"),
        InlineKeyboardButton("⚖ Судья", callback_data="role_judge"),
        InlineKeyboardButton("🎯 Прокурор", callback_data="role_prosecutor"),
        InlineKeyboardButton("🛡 Адвокат", callback_data="role_lawyer"),
        InlineKeyboardButton("🧨 Мститель", callback_data="role_avenger"),
        InlineKeyboardButton("👤 Гражданин", callback_data="role_citizen"),
    )

    await callback.message.answer("🎭 Выберите роль:", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("role_"))
async def role_info(callback: types.CallbackQuery):

    role = callback.data.split("_")[1]

    descriptions = {
        "detective": "🕵 Детектив\nМожет использовать /check 1 раз за раунд.",
        "judge": "⚖ Судья\nЕго голос считается за 2.",
        "prosecutor": "🎯 Прокурор\nМожет использовать /accuse 1 раз за игру.",
        "lawyer": "🛡 Адвокат\nМожет использовать /protect 1 раз за раунд.",
        "avenger": "🧨 Мститель\nЕсли его казнили — может использовать /revenge @username.",
        "citizen": "👤 Гражданин\nОбычный участник голосования."
    }

    await callback.message.answer(descriptions[role])
    await callback.answer()


# =======================
# СОЗДАНИЕ ИГРЫ
# =======================

@dp.callback_query_handler(lambda c: c.data == "create_game")
async def create_game(callback: types.CallbackQuery):
    await callback.message.answer("Добавьте бота в группу и напишите /join")
    await callback.answer()


# =======================
# JOIN
# =======================

@dp.message_handler(commands=['join'])
async def join(message: types.Message):
    global game_active

    if message.chat.type == "private":
        return

    if game_active:
        await message.answer("Игра уже идёт.")
        return

    if message.from_user.id not in players:
        players.append(message.from_user.id)
        await message.answer(f"Игроков: {len(players)}")

        if len(players) >= 4:
            await start_game(message.chat.id)


# =======================
# СТАРТ ИГРЫ
# =======================

async def start_game(chat_id):
    global game_active, roles, round_number

    game_active = True
    round_number = 0
    roles.clear()

    shuffled = players.copy()
    random.shuffle(shuffled)

    roles[shuffled[0]] = "detective"
    roles[shuffled[1]] = "judge"
    roles[shuffled[2]] = "prosecutor"

    index = 3

    if len(players) >= 6:
        roles[shuffled[index]] = "lawyer"
        index += 1
        roles[shuffled[index]] = "avenger"

    for p in players:
        if p not in roles:
            roles[p] = "citizen"

    for user_id, role in roles.items():
        await bot.send_message(user_id, f"🎭 Ваша роль: {role}")

    await start_round(chat_id)


# =======================
# РАУНД
# =======================

async def start_round(chat_id):
    global round_number, current_accused, truth, votes
    global lawyer_used, prosecutor_used, detective_used

    votes.clear()
    lawyer_used = False
    detective_used = False
    prosecutor_used = False

    round_number += 1

    current_accused = random.choice(players)
    truth = random.choice(["guilty", "innocent"])

    user = await bot.get_chat(current_accused)

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔴 Казнить", callback_data="guilty"),
        InlineKeyboardButton("🟢 Оправдать", callback_data="innocent")
    )

    await bot.send_message(
        chat_id,
        f"⚖️ Раунд {round_number}/{max_rounds}\n"
        f"Обвиняемый: @{user.username if user.username else user.first_name}",
        reply_markup=keyboard
    )

    await asyncio.sleep(20)
    await finish_round(chat_id)


# =======================
# ГОЛОСОВАНИЕ
# =======================

@dp.callback_query_handler(lambda c: c.data in ["guilty", "innocent"])
async def vote(callback: types.CallbackQuery):

    if callback.from_user.id == current_accused:
        await callback.answer("Обвиняемый не голосует.", show_alert=True)
        return

    votes[callback.from_user.id] = callback.data
    await callback.answer("Голос принят.")


# =======================
# СПЕЦРОЛИ
# =======================

@dp.message_handler(commands=['check'])
async def detective_check(message: types.Message):
    global detective_used

    if roles.get(message.from_user.id) != "detective":
        return

    if detective_used:
        await message.answer("Уже использовано.")
        return

    detective_used = True
    await message.answer(f"Истина: {truth}")


@dp.message_handler(commands=['protect'])
async def protect(message: types.Message):
    global lawyer_used

    if roles.get(message.from_user.id) != "lawyer":
        return

    if lawyer_used:
        await message.answer("Уже использовано.")
        return

    for user_id, vote in votes.items():
        if vote == "guilty":
            votes[user_id] = "neutral"
            lawyer_used = True
            await message.answer("🛡 Голос отменён.")
            break


@dp.message_handler(commands=['accuse'])
async def accuse(message: types.Message):
    global current_accused, prosecutor_used

    if roles.get(message.from_user.id) != "prosecutor":
        return

    if prosecutor_used:
        await message.answer("Уже использовано.")
        return

    prosecutor_used = True

    candidates = [p for p in players if p != message.from_user.id]
    current_accused = random.choice(candidates)

    user = await bot.get_chat(current_accused)
    await message.answer(f"🎯 Новый обвиняемый: @{user.username}")


@dp.message_handler(commands=['revenge'])
async def revenge(message: types.Message):
    if roles.get(message.from_user.id) != "avenger":
        return

    args = message.get_args()
    if not args:
        return

    username = args.replace("@", "")

    for p in players:
        user = await bot.get_chat(p)
        if user.username == username:
            players.remove(p)
            await message.answer(f"🧨 Мститель забрал @{username} с собой!")
            break


# =======================
# ЗАВЕРШЕНИЕ РАУНДА
# =======================

async def finish_round(chat_id):
    global game_active

    guilty_votes = 0
    innocent_votes = 0

    for user_id, vote in votes.items():
        multiplier = 2 if roles.get(user_id) == "judge" else 1

        if vote == "guilty":
            guilty_votes += multiplier
        elif vote == "innocent":
            innocent_votes += multiplier

    public_verdict = "guilty" if guilty_votes > innocent_votes else "innocent"

    for p in players:
        add_game(p)
        update_money(p, 20)
        update_exp(p, 30)

    if public_verdict == truth:
        for user_id in votes:
            if votes[user_id] == truth:
                add_win(user_id)
                update_money(user_id, 30)

    if round_number < max_rounds:
        await start_round(chat_id)
    else:
        game_active = False
        players.clear()
        await bot.send_message(chat_id, "🏆 Игра окончена!")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
