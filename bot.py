from dotenv import load_dotenv
import asyncio, logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from enum import Enum

load_dotenv()

waiting_players = []
active_games = {}
ready_players = set()
game_settings = {}

VICTORY_STICKER = "CAACAgIAAxkBAAELJEZl8mI7AAGeuI1P-AABu5AAAdOWLxsqPQACEgADQbVWDGq3-RpIOilHNAQ"
DEFAULT_ROUNDS = 1
DEFAULT_PLAYERS = 2

# Инициализация бота
def load_token():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("Bot token not set")
    return token

try:
    Token = load_token()
except ValueError as e:
    print("Error loading token")
    exit(1)

bot = Bot(Token)
dp = Dispatcher()

load_dotenv()

waiting_players = []
active_games = {}
ready_players = set()
game_settings = {}

VICTORY_STICKER = "CAACAgIAAxkBAAELJEZl8mI7AAGeuI1P-AABu5AAAdOWLxsqPQACEgADQbVWDGq3-RpIOilHNAQ"
DEFAULT_ROUNDS = 1
DEFAULT_PLAYERS = 2


class Move(Enum):
    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"


class RockPaperScissorsGame:
    def __init__(self, player1_id, player2_id, rounds=DEFAULT_ROUNDS):
        self.player1_id = player1_id
        self.player2_id = player2_id
        self.moves = {}
        self.status = "waiting_for_moves"
        self.total_rounds = rounds
        self.current_round = 1
        self.scores = {player1_id: 0, player2_id: 0}

    def make_move(self, player_id, move):
        if player_id not in [self.player1_id, self.player2_id]:
            raise ValueError("Invalid player")
        if self.status != "waiting_for_moves":
            raise ValueError("Game is not in progress")

        self.moves[player_id] = Move(move)

        if len(self.moves) == 2:
            winner = self.determine_winner()
            if winner:
                self.scores[winner] += 1

            if self.current_round < self.total_rounds:
                self.current_round += 1
                self.moves.clear()
                return "next_round", winner
            else:
                self.status = "finished"
                final_winner = max(self.scores.items(), key=lambda x: x[1])[0]
                return "game_over", final_winner
        return None, None

    def determine_winner(self):
        move1 = self.moves[self.player1_id]
        move2 = self.moves[self.player2_id]

        if move1 == move2:
            return None

        winning_moves = {
            Move.ROCK: Move.SCISSORS,
            Move.PAPER: Move.ROCK,
            Move.SCISSORS: Move.PAPER
        }

        if winning_moves[move1] == move2:
            return self.player1_id
        return self.player2_id


# Часть 2: Клавиатуры и вспомогательные функции
def create_move_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="🪨 Камень", callback_data="move_rock"),
            InlineKeyboardButton(text="✂️ Ножницы", callback_data="move_scissors"),
            InlineKeyboardButton(text="📄 Бумага", callback_data="move_paper")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def create_settings_keyboard():
    buttons = [
        [InlineKeyboardButton(text="Раунды: 1", callback_data="rounds_1"),
         InlineKeyboardButton(text="Раунды: 3", callback_data="rounds_3"),
         InlineKeyboardButton(text="Раунды: 5", callback_data="rounds_5")],
        [InlineKeyboardButton(text="Игроки: 2", callback_data="players_2"),
         InlineKeyboardButton(text="Игроки: 3", callback_data="players_3"),
         InlineKeyboardButton(text="Игроки: 4", callback_data="players_4")],
        [InlineKeyboardButton(text="Свои настройки", callback_data="custom_settings")],
        [InlineKeyboardButton(text="✅ Начать игру", callback_data="start_with_settings")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


# Часть 3: Команды и хендлеры
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id

    for game in active_games.values():
        if user_id in game["players"]:
            await message.answer("Вы уже участвуете в игре!")
            return

    game_settings[user_id] = {"rounds": DEFAULT_ROUNDS, "players": DEFAULT_PLAYERS}
    await message.answer(
        f"Привет, {message.from_user.first_name}! Выберите настройки игры или используйте /join для быстрого старта:",
        reply_markup=create_settings_keyboard()
    )


@dp.message(Command("join"))
async def join_waiting_command(message: types.Message):
    global waiting_players
    user_id = message.from_user.id

    for game in active_games.values():
        if user_id in game["players"]:
            await message.answer("Вы уже участвуете в игре!")
            return

    if user_id in waiting_players:
        await message.answer("Вы уже в листе ожидания")
    else:
        waiting_players.append(user_id)
        required_players = game_settings.get(user_id, {}).get('players', DEFAULT_PLAYERS)
        await message.answer(f"Вы в листе ожидания. Всего игроков: {len(waiting_players)}/{required_players}")

        if len(waiting_players) >= 2:
            other_players = [p for p in waiting_players if p != user_id]
            for player in other_players:
                if player not in ready_players:
                    await message.bot.send_message(
                        player,
                        f"Игрок {message.from_user.first_name} присоединился! Нажмите /ready если готовы начать"
                    )


@dp.message(Command("ready"))
async def ready_command(message: types.Message):
    global ready_players, waiting_players
    user_id = message.from_user.id

    if user_id not in waiting_players:
        await message.answer("Вы должны сначала присоединиться к игре командой /join")
        return

    if user_id in ready_players:
        await message.answer("Вы уже готовы к игре!")
        return

    ready_players.add(user_id)
    player_number = waiting_players.index(user_id) + 1

    for waiting_player in waiting_players:
        if waiting_player == user_id:
            await message.answer(f"Вы готовы к игре! Вы - Игрок {player_number}")
        else:
            await message.bot.send_message(
                waiting_player,
                f"Игрок {message.from_user.first_name} (Игрок {player_number}) готов к игре! Напишите /ready чтобы начать"
            )

    if len(ready_players) >= 2 and len(waiting_players) >= 2:
        players_to_start = [p for p in waiting_players if p in ready_players][:2]
        if len(players_to_start) >= 2:
            rounds = game_settings.get(players_to_start[0], {}).get('rounds', DEFAULT_ROUNDS)
            for player_id in players_to_start:
                await message.bot.send_message(player_id,
                                               f"Все игроки готовы! Игра начинается! Всего раундов: {rounds}")
            await asyncio.sleep(1)
            await start_game(players_to_start[0], players_to_start[1], message.bot, rounds)
            ready_players.remove(players_to_start[0])
            ready_players.remove(players_to_start[1])


@dp.message(Command("leave"))
async def leave_waiting_players(message: types.Message):
    global waiting_players, ready_players
    user_id = message.from_user.id
    if user_id in waiting_players:
        waiting_players.remove(user_id)
        if user_id in ready_players:
            ready_players.remove(user_id)
        await message.answer("Вы исключены из листа ожидания")
    else:
        await message.answer("Вы не в списке ожидания")


@dp.callback_query(lambda c: c.data.startswith(('rounds_', 'players_', 'start_with_', 'custom_')))
async def process_settings(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if data.startswith('rounds_'):
        rounds = int(data.split('_')[1])
        game_settings[user_id] = game_settings.get(user_id, {})
        game_settings[user_id]['rounds'] = rounds
        await callback_query.answer(f"Установлено {rounds} раундов")

    elif data.startswith('players_'):
        players = int(data.split('_')[1])
        game_settings[user_id] = game_settings.get(user_id, {})
        game_settings[user_id]['players'] = players
        await callback_query.answer(f"Установлено {players} игроков")

    elif data == 'custom_settings':
        await callback_query.answer()
        await callback_query.message.answer(
            "Введите свои настройки командой:\n"
            "/settings <кол-во раундов> <кол-во игроков>\n"
            "Например: /settings 7 3\n\n"
            "Ограничения:\n"
            "- Раунды: от 1 до 15\n"
            "- Игроки: от 2 до 10"
        )

    elif data == 'start_with_settings':
        settings = game_settings.get(user_id, {})
        rounds = settings.get('rounds', DEFAULT_ROUNDS)
        players = settings.get('players', DEFAULT_PLAYERS)
        await callback_query.answer()
        await callback_query.message.edit_text(
            f"Настройки игры:\n"
            f"Количество раундов: {rounds}\n"
            f"Количество игроков: {players}\n\n"
            f"Используйте /join чтобы присоединиться к игре с выбранными настройками"
        )
@dp.message(Command("games"))
async def list_games(message: types.Message):
    if not active_games:
        await message.answer("Нет активных игр")
        return

    games_list = []
    for game_id, info in active_games.items():
        game = info["game"]
        round_info = f"(Раунд {game.current_round}/{game.total_rounds})"
        games_list.append(f"Игра #{game_id}: {len(info['players'])} игроков {round_info}")

    await message.answer("Список активных игр:\n" + "\n".join(games_list))


@dp.message(Command("settings"))
async def custom_settings_command(message: types.Message):
    try:
        _, rounds, players = message.text.split()
        rounds = int(rounds)
        players = int(players)

        if rounds < 1 or players < 2:
            await message.answer("Количество раундов должно быть больше 0, а игроков больше 1")
            return

        if rounds > 15 or players > 10:
            await message.answer("Максимум 15 раундов и 10 игроков")
            return

        user_id = message.from_user.id
        game_settings[user_id] = {
            'rounds': rounds,
            'players': players
        }

        await message.answer(
            f"Установлены настройки:\n"
            f"Количество раундов: {rounds}\n"
            f"Количество игроков: {players}\n"
            f"Используйте /join чтобы начать игру"
        )

    except ValueError:
        await message.answer(
            "Неправильный формат. Используйте:\n"
            "/settings раунды игроки\n"
            "Например: /settings 7 3"
        )


# Часть 4: Игровая логика и коллбэки
async def start_game(player1_id, player2_id, bot, rounds=DEFAULT_ROUNDS):
    try:
        game = RockPaperScissorsGame(player1_id, player2_id, rounds)
        game_id = len(active_games) + 1
        active_games[game_id] = {
            "game": game,
            "players": [player1_id, player2_id]
        }

        for player_id in [player1_id, player2_id]:
            if player_id in waiting_players:
                waiting_players.remove(player_id)

        keyboard = create_move_keyboard()

        await bot.send_message(player1_id, f"Раунд {game.current_round}. Сделайте свой ход:", reply_markup=keyboard)
        await asyncio.sleep(0.5)
        await bot.send_message(player2_id, f"Раунд {game.current_round}. Сделайте свой ход:", reply_markup=keyboard)

    except Exception as e:
        logging.error(f"Error starting game: {e}")
        error_message = "Произошла ошибка при запуске игры. Попробуйте снова."
        for player_id in [player1_id, player2_id]:
            try:
                await bot.send_message(player_id, error_message)
            except:
                pass


@dp.callback_query(lambda c: c.data.startswith('move_'))
async def process_move(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    move = callback_query.data.split('_')[1]

    game_id = None
    for gid, game_info in active_games.items():
        if user_id in game_info["players"]:
            game_id = gid
            break

    if game_id is None:
        await callback_query.answer("Вы не участвуете в игре!")
        return

    game = active_games[game_id]["game"]

    try:
        status, winner = game.make_move(user_id, move)
        await callback_query.answer("Ход сделан!")

        if status == "next_round":
            if winner:
                winner_info = await callback_query.bot.get_chat(winner)
                round_result = f"Раунд выиграл {winner_info.first_name}!"
            else:
                round_result = "Ничья!"

            for player_id in [game.player1_id, game.player2_id]:
                keyboard = create_move_keyboard()
                await callback_query.bot.send_message(
                    player_id,
                    f"{round_result}\nРаунд {game.current_round}. Сделайте ход:",
                    reply_markup=keyboard
                )

        elif status == "game_over":
            try:
                winner_info = await callback_query.bot.get_chat(winner)
                winner_name = winner_info.first_name
            except:
                winner_name = "Неизвестный игрок"

            for player_id in [game.player1_id, game.player2_id]:
                if player_id == winner:
                    await callback_query.bot.send_message(
                        player_id,
                        f"Поздравляем! Вы победили со счетом {game.scores[winner]}:{game.scores[game.player1_id if winner == game.player2_id else game.player2_id]}"
                    )
                    await callback_query.bot.send_sticker(player_id, VICTORY_STICKER)
                else:
                    await callback_query.bot.send_message(
                        player_id,
                        f"Игра окончена! Победил {winner_name} со счетом {game.scores[winner]}:{game.scores[player_id]}"
                    )

            del active_games[game_id]

    except ValueError as e:
        await callback_query.answer(str(e))


# Часть 5: Запуск бота
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(dp.start_polling(bot))
    except Exception as e:
        logging.error(f"Error occurred: {e}")