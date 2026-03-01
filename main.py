import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

players = []
roles = {}
scores = {}
votes = {}

game_active = False
round_number = 0
max_rounds = 3

current_accused = None
truth = None


# ---------------- START ----------------

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎮 Создать игру", callback_data="create_game"))
    await message.answer("⚖️ Суд народа 3.0\n\nНажмите, чтобы создать игру.", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == "create_game")
async def create_game(callback: types.CallbackQuery):
    global players, roles, scores, votes, game_active, round_number
    players = []
    roles = {}
    scores = {}
    votes = {}
    round_number = 0
    game_active = False

    await callback.message.answer("Игра создана!\nНапишите /join чтобы присоединиться.")
    await callback.answer()


@dp.message_handler(commands=['join'])
async def join_game(message: types.Message):
    global game_active

    if game_active:
        await message.answer("Игра уже идёт.")
        return

    if message.from_user.id not in players:
        players.append(message.from_user.id)
        scores[message.from_user.id] = 0
        await message.answer(f"Вы присоединились! Игроков: {len(players)}")

        if len(players) == 4:
            await assign_roles(message.chat.id)
            game_active = True
            await start_round(message.chat.id)

    else:
        await message.answer("Вы уже в игре.")


# ---------------- ROLES ----------------

async def assign_roles(chat_id):
    global roles

    shuffled = players.copy()
    random.shuffle(shuffled)

    roles[shuffled[0]] = "detective"
    roles[shuffled[1]] = "judge"
    roles[shuffled[2]] = "provocator"

    for p in players:
        if p not in roles:
            roles[p] = "citizen"

    for user_id in players:
        role = roles[user_id]
        if role == "detective":
            text = "🕵 Вы — Детектив. Используйте /check (1 раз за раунд)."
        elif role == "judge":
            text = "⚖ Вы — Судья. Ваш голос считается за 2."
        elif role == "provocator":
            text = "😈 Вы — Провокатор. Получаете очки если толпа ошибётся."
        else:
            text = "👤 Вы — Гражданин. Голосуйте правильно."

        await bot.send_message(user_id, text)


# ---------------- ROUND ----------------

async def start_round(chat_id):
    global round_number, current_accused, truth, votes

    votes = {}
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
        f"Голосование 25 секунд.",
        reply_markup=keyboard
    )

    await asyncio.sleep(25)
    await finish_round(chat_id)


# ---------------- DETECTIVE ----------------

@dp.message_handler(commands=['check'])
async def detective_check(message: types.Message):
    if roles.get(message.from_user.id) != "detective":
        return

    if truth == "guilty":
        await message.answer("🔎 Истина: ВИНОВЕН.")
    else:
        await message.answer("🔎 Истина: НЕВИНОВЕН.")


# ---------------- VOTING ----------------

@dp.callback_query_handler(lambda c: c.data in ["guilty", "innocent"])
async def vote_handler(callback: types.CallbackQuery):

    if callback.from_user.id not in players:
        await callback.answer("Вы не участвуете.", show_alert=True)
        return

    if callback.from_user.id == current_accused:
        await callback.answer("Обвиняемый не голосует!", show_alert=True)
        return

    if callback.from_user.id in votes:
        await callback.answer("Вы уже голосовали!", show_alert=True)
        return

    votes[callback.from_user.id] = callback.data
    await callback.answer("Голос принят.")


# ---------------- FINISH ROUND ----------------

async def finish_round(chat_id):
    guilty_votes = 0
    innocent_votes = 0

    for user_id, vote in votes.items():
        multiplier = 2 if roles.get(user_id) == "judge" else 1

        if vote == "guilty":
            guilty_votes += multiplier
        else:
            innocent_votes += multiplier

    if guilty_votes > innocent_votes:
        public_verdict = "guilty"
    else:
        public_verdict = "innocent"

    result_text = f"\n📊 Голоса:\n🔴 {guilty_votes}\n🟢 {innocent_votes}\n\n"

    if public_verdict == truth:
        result_text += "✅ Толпа права!\n"
        for user_id, vote in votes.items():
            if vote == truth:
                scores[user_id] += 1
    else:
        result_text += "❌ Толпа ошиблась!\n"
        for user_id in players:
            if roles[user_id] == "provocator":
                scores[user_id] += 2

        if truth == "innocent" and public_verdict == "guilty":
            scores[current_accused] += 1

    result_text += f"Истина: {'ВИНОВЕН' if truth == 'guilty' else 'НЕВИНОВЕН'}"

    await bot.send_message(chat_id, result_text)

    if round_number < max_rounds:
        await asyncio.sleep(3)
        await start_round(chat_id)
    else:
        await end_game(chat_id)


# ---------------- END GAME ----------------

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
