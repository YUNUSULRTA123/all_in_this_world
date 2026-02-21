import sqlite3

import telebot
from telebot import types

from config import TOKEN

bot = telebot.TeleBot(TOKEN)
DB_PATH = "data.db"
AWAITING_SPECIALIST: set[int] = set()


def faq() -> list[tuple[str, str, str]]:
    return [
        (
            "Как оформить заказ?",
            "Для оформления заказа, пожалуйста, выберите интересующий вас товар и нажмите кнопку 'Добавить в корзину', затем перейдите в корзину и следуйте инструкциям для завершения покупки.",
            "заказ,оформить,купить,корзина",
        ),
        (
            "Как узнать статус моего заказа?",
            "Вы можете узнать статус вашего заказа, войдя в свой аккаунт на нашем сайте и перейдя в раздел 'Мои заказы'. Там будет указан текущий статус вашего заказа.",
            "статус,заказ,где заказ,отследить",
        ),
        (
            "Как отменить заказ?",
            "Если вы хотите отменить заказ, пожалуйста, свяжитесь с нашей службой поддержки как можно скорее. Мы постараемся помочь вам с отменой заказа до его отправки.",
            "отменить,отмена,вернуть заказ",
        ),
        (
            "Что делать, если товар пришел поврежденным?",
            "При получении поврежденного товара, пожалуйста, сразу свяжитесь с нашей службой поддержки и предоставьте фотографии повреждений. Мы поможем вам с обменом или возвратом товара.",
            "поврежден,сломанный,брак,дефект,обмен,возврат",
        ),
        (
            "Как связаться с вашей технической поддержкой?",
            "Вы можете связаться с нашей технической поддержкой через телефон на нашем сайте или написать нам в чат-бота.",
            "поддержка,техподдержка,помощь,оператор,связаться",
        ),
        (
            "Как узнать информацию о доставке?",
            "Информацию о доставке вы можете найти на странице оформления заказа на нашем сайте. Там указаны доступные способы доставки и сроки.",
            "доставка,сроки,курьер,получение",
        ),
    ]


def build_main_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("FAQ", "Связаться со специалистом")
    keyboard.row("Помощь")
    return keyboard


def seed_faq_if_empty(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS faq (question TEXT, answer TEXT, keywords TEXT)"
    )

    row_count = cur.execute("SELECT COUNT(*) FROM faq").fetchone()[0]
    if row_count == 0:
        cur.executemany(
            "INSERT INTO faq (question, answer, keywords) VALUES (?, ?, ?)",
            faq(),
        )
        conn.commit()

    conn.close()


def init_database(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS specialist_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            full_name TEXT,
            message_type TEXT NOT NULL,
            message_text TEXT,
            voice_file_id TEXT,
            status TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()
    seed_faq_if_empty(db_path)


def save_specialist_request(message, message_type: str) -> None:
    text = message.text if message_type == "text" else None
    voice_file_id = message.voice.file_id if message_type == "voice" else None
    full_name = " ".join(
        part for part in [message.from_user.first_name, message.from_user.last_name] if part
    )

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO specialist_requests (
            user_id, username, full_name, message_type, message_text, voice_file_id
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            message.from_user.id,
            message.from_user.username,
            full_name,
            message_type,
            text,
            voice_file_id,
        ),
    )
    conn.commit()
    conn.close()


def find_faq_answer(query: str) -> tuple[str, str] | None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = cur.execute("SELECT question, answer, keywords FROM faq").fetchall()
    conn.close()

    user_query = query.strip().lower()
    for question, answer, keywords in rows:
        question_match = user_query in question.lower() or question.lower() in user_query
        keyword_match = any(
            kw.strip().lower() in user_query for kw in keywords.split(",") if kw.strip()
        )
        if question_match or keyword_match:
            return question, answer
    return None


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Приветствую тебя, я ТГ бот техподдержки интернет-магазина 'Всё на свете'. "
        "Я помогу тебе решить вопрос: покажу FAQ или передам запрос специалисту.",
        reply_markup=build_main_keyboard(),
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "Список доступных команд:\n"
        "/start - начать общение с ботом\n"
        "/help - получить список доступных команд\n"
        "/faq - показать список FAQ\n"
        "/faq <вопрос> - найти ответ в FAQ\n"
        "/specialist - отправить запрос специалисту",
        reply_markup=build_main_keyboard(),
    )


@bot.message_handler(commands=["faq"])
def faq_command(message):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = cur.execute("SELECT question, answer, keywords FROM faq").fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "FAQ пока пуст. Попробуйте позже.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) == 1:
        questions = ["Часто задаваемые вопросы:"]
        for i, (question, _, _) in enumerate(rows, start=1):
            questions.append(f"{i}. {question}")
        questions.append("\nНапишите: /faq <ваш вопрос>")
        bot.send_message(message.chat.id, "\n".join(questions), reply_markup=build_main_keyboard())
        return

    user_query = parts[1].strip().lower()
    for question, answer, keywords in rows:
        question_match = user_query in question.lower() or question.lower() in user_query
        keyword_match = any(
            kw.strip().lower() in user_query for kw in keywords.split(",") if kw.strip()
        )
        if question_match or keyword_match:
            bot.send_message(message.chat.id, f"{question}\n\n{answer}", reply_markup=build_main_keyboard())
            return

    bot.send_message(
        message.chat.id,
        "Не нашёл точный ответ в FAQ. Попробуйте переформулировать вопрос.",
        reply_markup=build_main_keyboard(),
    )


@bot.message_handler(commands=["specialist"])
def specialist_command(message):
    AWAITING_SPECIALIST.add(message.chat.id)
    bot.send_message(
        message.chat.id,
        "Опишите проблему текстом или отправьте голосовое сообщение. "
        "Я сохраню запрос и передам специалисту.",
        reply_markup=build_main_keyboard(),
    )


@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    save_specialist_request(message, "voice")
    AWAITING_SPECIALIST.discard(message.chat.id)
    bot.send_message(
        message.chat.id,
        "Голосовое сообщение сохранено и передано специалисту. "
        "Ожидайте ответ от команды поддержки.",
        reply_markup=build_main_keyboard(),
    )


@bot.message_handler(content_types=["text"])
def handle_text(message):
    text = message.text.strip()

    if text == "FAQ":
        faq_command(message)
        return
    if text == "Связаться со специалистом":
        specialist_command(message)
        return
    if text == "Помощь":
        help_command(message)
        return
    if text.startswith("/"):
        return

    if message.chat.id in AWAITING_SPECIALIST:
        save_specialist_request(message, "text")
        AWAITING_SPECIALIST.discard(message.chat.id)
        bot.send_message(
            message.chat.id,
            "Запрос сохранён и передан специалисту. "
            "Если нужно, вы можете отправить ещё одно обращение через /specialist.",
            reply_markup=build_main_keyboard(),
        )
        return

    faq_result = find_faq_answer(text)
    if faq_result:
        question, answer = faq_result
        bot.send_message(message.chat.id, f"{question}\n\n{answer}", reply_markup=build_main_keyboard())
        return

    bot.send_message(
        message.chat.id,
        "Не нашёл ответ в FAQ. Нажмите 'Связаться со специалистом' или используйте /specialist.",
        reply_markup=build_main_keyboard(),
    )


if __name__ == "__main__":
    init_database()
    bot.infinity_polling()
