import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ---------------- ДАННЫЕ ----------------

players = []
roles = {}
scores = {}
votes = {}

game_active = False
round_number = 0
max_rounds = 3

current_accused = None
truth = None

detective_used = False
prosecutor_used = False

user_language = {}


# ---------------- ГЛАВНОЕ МЕНЮ ----------------

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🔥 Начать суд", callback_data="create_game"),
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("🌍 Сменить язык", callback_data="language"),
        InlineKeyboardButton("🎭 Роли", callback_data="roles_info"),
        InlineKeyboardButton("➕ Добавить в группу", url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true")
    )

    await message.answer(
        "━━━━━━━━━━━━━━━━\n"
        "⚖️ СУД НАРОДА\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "Толпа решает судьбу.\n"
        "Но истина скрыта.\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )


# ---------------- ПРОФИЛЬ ----------------

@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile_handler(callback: types.CallbackQuery):

    score = scores.get(callback.from_user.id, 0)
    role = roles.get(callback.from_user.id, "Нет")

    await callback.message.answer(
        f"👤 Профиль\n\n"
        f"Очков: {score}\n"
        f"Текущая роль: {role}"
    )

    await callback.answer()


# ---------------- ЯЗЫК ----------------

@dp.callback_query_handler(lambda c: c.data == "language")
async def language_menu(callback: types.CallbackQuery):

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
    user_language[callback.from_user.id] = lang

    await callback.message.answer("Язык обновлён.")
    await callback.answer()


# ---------------- РОЛИ ИНФО ----------------

@dp.callback_query_handler(lambda c: c.data == "roles_info")
async def roles_info(callback: types.CallbackQuery):

    await callback.message.answer(
        "🎭 Роли:\n\n"
        "🕵 Детектив — /check (1 раз за раунд)\n"
        "⚖ Судья — голос ×2\n"
        "🎯 Прокурор — /accuse (1 раз за игру)\n"
        "👤 Гражданин — голосует"
    )

    await callback.answer()


# ---------------- СОЗДАНИЕ ИГРЫ ----------------

@dp.callback_query_handler(lambda c: c.data == "create_game")
async def create_game(callback: types.CallbackQuery):
    global players, roles, votes, round_number, game_active
    global detective_used, prosecutor_used

    players = []
    roles = {}
    votes = {}
    round_number = 0
    game_active = False
    detective_used = False
    prosecutor_used = False

    await callback.message.answer("Игра создана!\nНапишите /join в группе.")
    await callback.answer()


# ---------------- JOIN ----------------

@dp.message_handler(commands=['join'])
async def join_game(message: types.Message):
    global game_active

    if message.chat.type == "private":
        await message.answer("Играть можно только в группе.")
        return

    if game_active:
        await message.answer("Игра уже идёт.")
        return

    if message.from_user.id not in players:
        players.append(message.from_user.id)
        scores.setdefault(message.from_user.id, 0)

        await message.answer(f"Игроков: {len(players)}")

        if len(players) >= 4:
            await assign_roles(message.chat.id)
            game_active = True
            await start_round(message.chat.id)


# ---------------- РАСПРЕДЕЛЕНИЕ РОЛЕЙ ----------------

async def assign_roles(chat_id):
    global roles

    shuffled = players.copy()
    random.shuffle(shuffled)

    roles[shuffled[0]] = "detective"
    roles[shuffled[1]] = "judge"
    roles[shuffled[2]] = "prosecutor"

    for p in players:
        if p not in roles:
            roles[p] = "citizen"

    for user_id in players:
        role = roles[user_id]

        if role == "detective":
            text = "🕵 Вы — Детектив. Используйте /check (1 раз за раунд)."
        elif role == "judge":
            text = "⚖ Вы — Судья. Ваш голос ×2."
        elif role == "prosecutor":
            text = "🎯 Вы — Прокурор. Используйте /accuse (1 раз за игру)."
        else:
            text = "👤 Вы — Гражданин."

        await bot.send_message(user_id, text)


# ---------------- НАЧАЛО РАУНДА ----------------

async def start_round(chat_id):
    global round_number, current_accused, truth, votes
    global detective_used

    votes = {}
    detective_used = False
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
        f"⚖️ Раунд {round_number}/{max_rounds}\n\n"
        f"🔴 Обвиняемый: @{user.username if user.username else user.first_name}\n\n"
        f"Голосование 20 секунд.",
        reply_markup=keyboard
    )

    await asyncio.sleep(20)
    await finish_round(chat_id)


# ---------------- ДЕТЕКТИВ ----------------

@dp.message_handler(commands=['check'])
async def detective_check(message: types.Message):
    global detective_used

    if roles.get(message.from_user.id) != "detective":
        return

    if detective_used:
        await message.answer("Вы уже использовали проверку.")
        return

    detective_used = True

    await message.answer(
        f"🔎 Истина: {'ВИНОВЕН' if truth == 'guilty' else 'НЕВИНОВЕН'}"
    )


# ---------------- ПРОКУРОР ----------------

@dp.message_handler(commands=['accuse'])
async def prosecutor_accuse(message: types.Message):
    global current_accused, prosecutor_used

    if roles.get(message.from_user.id) != "prosecutor":
        return

    if prosecutor_used:
        await message.answer("Вы уже использовали обвинение.")
        return

    prosecutor_used = True

    candidates = [p for p in players if p != message.from_user.id]
    current_accused = random.choice(candidates)

    user = await bot.get_chat(current_accused)

    await message.answer(
        f"🎯 Прокурор назначил обвиняемого!\n\n"
        f"🔴 Новый обвиняемый: @{user.username if user.username else user.first_name}"
    )


# ---------------- ГОЛОСОВАНИЕ ----------------

@dp.callback_query_handler(lambda c: c.data in ["guilty", "innocent"])
async def vote_handler(callback: types.CallbackQuery):

    if callback.from_user.id not in players:
        return

    if callback.from_user.id == current_accused:
        await callback.answer("Обвиняемый не голосует.", show_alert=True)
        return

    if callback.from_user.id in votes:
        await callback.answer("Вы уже голосовали.", show_alert=True)
        return

    votes[callback.from_user.id] = callback.data
    await callback.answer("Голос принят.")


# ---------------- ЗАВЕРШЕНИЕ РАУНДА ----------------

async def finish_round(chat_id):

    guilty_votes = 0
    innocent_votes = 0

    for user_id, vote in votes.items():
        multiplier = 2 if roles.get(user_id) == "judge" else 1

        if vote == "guilty":
            guilty_votes += multiplier
        else:
            innocent_votes += multiplier

    public_verdict = "guilty" if guilty_votes > innocent_votes else "innocent"

    result_text = f"\n📊 Голоса:\n🔴 {guilty_votes}\n🟢 {innocent_votes}\n\n"

    if public_verdict == truth:
        result_text += "✅ Толпа права!\n"
        for user_id, vote in votes.items():
            if vote == truth:
                scores[user_id] += 1
    else:
        result_text += "❌ Толпа ошиблась!\n"
        if truth == "innocent" and public_verdict == "guilty":
            scores[current_accused] += 1

    result_text += f"Истина: {'ВИНОВЕН' if truth == 'guilty' else 'НЕВИНОВЕН'}"

    await bot.send_message(chat_id, result_text)

    if round_number < max_rounds:
        await asyncio.sleep(3)
        await start_round(chat_id)
    else:
        await end_game(chat_id)


# ---------------- КОНЕЦ ИГРЫ ----------------

async def end_game(chat_id):

    winner = max(scores, key=scores.get)
    user = await bot.get_chat(winner)

    await bot.send_message(
        chat_id,
        f"🏆 Игра окончена!\n\n"
        f"Победитель: @{user.username if user.username else user.first_name}\n"
        f"Очков: {scores[winner]}"
    )


# ---------------- RUN ----------------

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
