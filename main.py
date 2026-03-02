import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

from config import BOT_TOKEN
from db import *
from economy import calculate_level

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

init_db()

# =============================
# ГЛОБАЛЬНОЕ СОСТОЯНИЕ
# =============================

game_active = False
game_chat_id = None
players = []
roles = {}
votes = {}

current_accused = None
truth = None
round_number = 0
max_rounds = 3

# =============================
# ОБВИНЕНИЯ
# =============================

COMMON_ACCUSATIONS = [
    "Украл печенье из офиса.",
    "Спал на рабочем месте.",
    "Опоздал на суд.",
    "Подделал отчёт.",
    "Сломал кофемашину."
]

RARE_ACCUSATIONS = [
    "Продал секретные документы.",
    "Подменил улики.",
    "Подкупил свидетеля.",
    "Скрыл важные доказательства."
]

LEGENDARY_ACCUSATIONS = [
    "Организовал тайный заговор против суда.",
    "Манипулировал системой правосудия.",
    "Создал фальшивую личность.",
    "Саботировал государственный процесс."
]

# =============================
# МЕНЮ
# =============================

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⚖️ Создать игру")
    kb.add("👤 Профиль", "🎭 Роли")
    kb.add("📜 Об игре", "🌍 Язык")
    kb.add("➕ Добавить в чат")
    return kb

# =============================
# КОМАНДЫ
# =============================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    register_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "⚖️ <b>СУД НАРОДА</b>\n\n"
        "Психологическая игра голосования.\n"
        "В каждом раунде один игрок становится обвиняемым.\n"
        "Истину знает только система.\n\n"
        "Выбери действие:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@dp.message_handler(commands=["profile"])
async def profile(message: types.Message):
    user = get_user(message.from_user.id)
    level = calculate_level(user[5])
    await message.answer(
        f"👤 @{message.from_user.username}\n\n"
        f"💰 Деньги: {user[3]}\n"
        f"💎 Алмазы: {user[4]}\n"
        f"⭐ Уровень: {level}\n"
        f"🏆 Победы: {user[6]}"
    )

@dp.message_handler(commands=["about"])
async def about(message: types.Message):
    await message.answer(
        "⚖️ <b>ОБ ИГРЕ</b>\n\n"
        "Игроки голосуют: виновен или нет.\n"
        "Если толпа угадывает — получает награду.\n"
        "Если ошибается — проигрывает.",
        parse_mode="HTML"
    )

@dp.message_handler(commands=["support"])
async def support(message: types.Message):
    await message.answer("Связь с разработчиком: @yourusername")

@dp.message_handler(commands=["join"])
async def join(message: types.Message):
    global players

    if message.from_user.id not in players:
        players.append(message.from_user.id)
        await message.answer("Вы присоединились к игре!")

# =============================
# СОЗДАНИЕ ИГРЫ
# =============================

@dp.message_handler(lambda m: m.text == "⚖️ Создать игру")
async def create_game(message: types.Message):
    global game_active, game_chat_id, players, round_number

    if game_active:
        await message.answer("Игра уже запущена.")
        return

    game_active = True
    game_chat_id = message.chat.id
    players = []
    round_number = 0

    await message.answer("Игра создана! Используйте /join чтобы войти.")

    await asyncio.sleep(10)

    if len(players) < 2:
        game_active = False
        await message.answer("Недостаточно игроков.")
        return

    await start_round()

# =============================
# РАУНД
# =============================

async def start_round():
    global round_number, current_accused, truth

    votes.clear()
    round_number += 1

    current_accused = random.choice(players)
    truth = random.choice(["guilty", "innocent"])

    roll = random.randint(1, 100)

    if roll <= 75:
        accusation = random.choice(COMMON_ACCUSATIONS)
        rarity_text = ""
    elif roll <= 95:
        accusation = random.choice(RARE_ACCUSATIONS)
        rarity_text = "\n🟡 Редкое обвинение!"
    else:
        accusation = random.choice(LEGENDARY_ACCUSATIONS)
        rarity_text = "\n🔴🔥 Легендарное обвинение!"

    user = await bot.get_chat(current_accused)

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔴 Казнить", callback_data="vote_guilty"),
        InlineKeyboardButton("🟢 Оправдать", callback_data="vote_innocent")
    )

    await bot.send_message(
        game_chat_id,
        f"⚖️ <b>РАУНД {round_number}</b>\n\n"
        f"👤 Обвиняемый: @{user.username}\n\n"
        f"📜 Обвинение:\n{accusation}"
        f"{rarity_text}",
        reply_markup=kb,
        parse_mode="HTML"
    )

    await asyncio.sleep(20)
    await finish_round()

# =============================
# ГОЛОСОВАНИЕ
# =============================

@dp.callback_query_handler(lambda c: c.data.startswith("vote_"))
async def vote(callback: types.CallbackQuery):
    votes[callback.from_user.id] = callback.data.split("_")[1]
    await callback.answer("Голос принят!")

# =============================
# ЗАВЕРШЕНИЕ
# =============================

async def finish_round():
    global game_active

    guilty_votes = list(votes.values()).count("guilty")
    innocent_votes = list(votes.values()).count("innocent")

    result = "guilty" if guilty_votes > innocent_votes else "innocent"

    if result == truth:
        text = "Толпа оказалась права!"
    else:
        text = "Толпа ошиблась!"

    await bot.send_message(game_chat_id, text)

    if round_number >= max_rounds:
        game_active = False
        await bot.send_message(game_chat_id, "Игра окончена.")
    else:
        await start_round()

# =============================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
