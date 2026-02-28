import sqlite3
import telebot
from telebot import types
from config import TOKEN

bot = telebot.TeleBot(TOKEN)
DB_PATH = "data.db"
AWAITING_SPECIALIST: set[int] = set()


def db(query, params=(), fetch=False, many=False):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.executemany(query, params) if many else cur.execute(query, params)
        return cur.fetchall() if fetch else None


def init_db():
    db("CREATE TABLE IF NOT EXISTS faq(question TEXT, answer TEXT, keywords TEXT)")
    db("""CREATE TABLE IF NOT EXISTS specialist_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, username TEXT, full_name TEXT,
            message_type TEXT, message_text TEXT, voice_file_id TEXT,
            status TEXT DEFAULT 'new',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    if not db("SELECT 1 FROM faq LIMIT 1", fetch=True):
        db("INSERT INTO faq VALUES (?,?,?)", faq(), many=True)


def faq():
    return [
        ("Как оформить заказ?", "Выберите товар → добавьте в корзину → оформите заказ.", "заказ,купить,корзина"),
        ("Как узнать статус заказа?", "Зайдите в аккаунт → Мои заказы.", "статус,отследить"),
        ("Как отменить заказ?", "Свяжитесь с поддержкой как можно скорее.", "отмена,вернуть"),
        ("Товар поврежден?", "Пришлите фото — оформим обмен/возврат.", "брак,дефект,возврат"),
        ("Как связаться с поддержкой?", "Напишите в бота или позвоните по телефону на сайте.", "поддержка,оператор"),
        ("Информация о доставке?", "Сроки и способы указаны при оформлении.", "доставка,курьер"),
    ]


def find_answer(text):
    text = text.lower()
    for q, a, k in db("SELECT question, answer, keywords FROM faq", fetch=True):
        if text in q.lower() or any(x in text for x in k.split(",")):
            return q, a


def kb():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("FAQ", "Связаться со специалистом")
    m.row("Помощь")
    return m


def save_request(msg, t):
    db("""INSERT INTO specialist_requests
          (user_id, username, full_name, message_type, message_text, voice_file_id)
          VALUES (?,?,?,?,?,?)""",
       (msg.from_user.id,
        msg.from_user.username,
        f"{msg.from_user.first_name or ''} {msg.from_user.last_name or ''}".strip(),
        t,
        msg.text if t == "text" else None,
        msg.voice.file_id if t == "voice" else None))


@bot.message_handler(commands=["start"])
def start(m):
    bot.send_message(m.chat.id, "Привет! Я бот техподдержки. Помогу с FAQ или соединю со специалистом.", reply_markup=kb())


@bot.message_handler(commands=["help"])
def help_cmd(m):
    bot.send_message(m.chat.id, "/faq /specialist /help", reply_markup=kb())


@bot.message_handler(commands=["faq"])
def faq_cmd(m):
    parts = m.text.split(maxsplit=1)

    if len(parts) == 1:
        qs = db("SELECT question FROM faq", fetch=True)
        text = "FAQ:\n" + "\n".join(f"{i+1}. {q[0]}" for i, q in enumerate(qs))
        return bot.send_message(m.chat.id, text, reply_markup=kb())

    ans = find_answer(parts[1])
    bot.send_message(m.chat.id, "\n\n".join(ans) if ans else "Ответ не найден.", reply_markup=kb())


@bot.message_handler(commands=["specialist"])
def specialist(m):
    AWAITING_SPECIALIST.add(m.chat.id)
    bot.send_message(m.chat.id, "Опишите проблему текстом или голосом.", reply_markup=kb())


@bot.message_handler(content_types=["voice"])
def voice(m):
    save_request(m, "voice")
    AWAITING_SPECIALIST.discard(m.chat.id)
    bot.send_message(m.chat.id, "Передано специалисту.", reply_markup=kb())


@bot.message_handler(content_types=["text"])
def text(m):
    t = m.text.strip()

    if t == "FAQ":
        return faq_cmd(m)
    if t == "Связаться со специалистом":
        return specialist(m)
    if t == "Помощь":
        return help_cmd(m)
    if t.startswith("/"):
        return

    if m.chat.id in AWAITING_SPECIALIST:
        save_request(m, "text")
        AWAITING_SPECIALIST.discard(m.chat.id)
        return bot.send_message(m.chat.id, "Передано специалисту.", reply_markup=kb())

    ans = find_answer(t)
    bot.send_message(m.chat.id, "\n\n".join(ans) if ans else "Не нашёл ответ. Нажмите 'Связаться со специалистом'.", reply_markup=kb())


if __name__ == "__main__":
    init_db()
    bot.infinity_polling()
