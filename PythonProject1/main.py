import telebot
import sqlite3
from telebot import types

# ---------------- НАЛАШТУВАННЯ ----------------
bot = telebot.TeleBot("8234314802:AAFa5w9U7uIBnlmsCYapWUSjOpjw0KOBvl8")
ADMIN_IDS = [799581078, 5195186514]

# ---------------- БАЗА ДАНИХ ----------------
conn = sqlite3.connect("library.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    date TEXT,
    time TEXT,
    location TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    phone TEXT,
    event_title TEXT
)
""")
conn.commit()

# ---------------- ГОЛОВНЕ МЕНЮ ----------------
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📅 Переглянути заходи")
    markup.add("✍️ Записатися на захід")
    return markup

# ---------------- /START ----------------
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "📚 Вітаємо в чат-боті Обласної бібліотеки для юнацтва ім. О. Гончара!",
        reply_markup=main_menu()
    )

# ---------------- ПЕРЕГЛЯД ЗАХОДІВ ----------------
@bot.message_handler(func=lambda m: m.text == "📅 Переглянути заходи")
def show_events(message):
    cursor.execute("SELECT id, title, date, time, location FROM events")
    events = cursor.fetchall()

    if not events:
        bot.send_message(message.chat.id, "Наразі заходів немає.")
        return

    text = "📅 Актуальні заходи:\n\n"
    for e in events:
        text += f"{e[0]}. {e[1]}\n📆 {e[2]} ⏰ {e[3]}\n📍 {e[4]}\n\n"

    bot.send_message(message.chat.id, text, reply_markup=main_menu())

# ---------------- ЗАПИС НА ЗАХІД ----------------
@bot.message_handler(func=lambda m: m.text == "✍️ Записатися на захід")
def register_start(message):
    cursor.execute("SELECT id, title FROM events")
    events = cursor.fetchall()

    text = "Оберіть номер заходу:\n"
    for e in events:
        text += f"{e[0]}. {e[1]}\n"

    bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(message, choose_event)

def choose_event(message):
    try:
        event_id = int(message.text)
        cursor.execute("SELECT title FROM events WHERE id=?", (event_id,))
        event = cursor.fetchone()
        if event:
            bot.send_message(message.chat.id, "Введіть ваше ім’я:")
            bot.register_next_step_handler(message, get_name, event[0])
        else:
            bot.send_message(message.chat.id, "❌ Невірний номер.")
    except:
        bot.send_message(message.chat.id, "❌ Введіть номер цифрами.")

def get_name(message, event_title):
    bot.send_message(message.chat.id, "Введіть номер телефону:")
    bot.register_next_step_handler(message, get_phone, message.text, event_title)

def get_phone(message, name, event_title):
    phone = message.text
    if not phone.isdigit():
        bot.send_message(message.chat.id, "❌ Невірний формат телефону. Введіть ще раз:")
        bot.register_next_step_handler(message, get_phone, name, event_title)
        return

    cursor.execute(
        "INSERT INTO registrations (user_id, name, phone, event_title) VALUES (?, ?, ?, ?)",
        (message.chat.id, name, phone, event_title)
    )
    conn.commit()

    bot.send_message(message.chat.id, "✅ Запис успішний!", reply_markup=main_menu())

# ================== АДМІН-ПАНЕЛЬ ==================
@bot.message_handler(commands=["admins"])
def admin_panel(message):
    if message.chat.id not in ADMIN_IDS:
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Переглянути записи")
    markup.add("➕ Додати захід", "✏️ Редагувати захід")
    markup.add("🗑 Очистити всі записи")
    markup.add("⬅️ Назад")
    bot.send_message(message.chat.id, "🔐 Адмін-панель", reply_markup=markup)

# ---------- ДОДАТИ ЗАХІД ----------
@bot.message_handler(func=lambda m: m.text == "➕ Додати захід")
def add_event_start(message):
    bot.send_message(message.chat.id, "Введіть назву заходу:")
    bot.register_next_step_handler(message, add_event_date)

def add_event_date(message):
    title = message.text
    bot.send_message(message.chat.id, "Введіть дату (дд.мм.рррр):")
    bot.register_next_step_handler(message, add_event_time, title)

def add_event_time(message, title):
    date = message.text
    bot.send_message(message.chat.id, "Введіть час (год:хв):")
    bot.register_next_step_handler(message, add_event_location, title, date)

def add_event_location(message, title, date):
    time = message.text
    bot.send_message(message.chat.id, "Введіть місце проведення:")
    bot.register_next_step_handler(message, save_event, title, date, time)

def save_event(message, title, date, time):
    location = message.text
    cursor.execute(
        "INSERT INTO events (title, date, time, location) VALUES (?, ?, ?, ?)",
        (title, date, time, location)
    )
    conn.commit()
    bot.send_message(message.chat.id, "✅ Захід додано")

# ---------- РЕДАГУВАТИ ЗАХІД ----------
@bot.message_handler(func=lambda m: m.text == "✏️ Редагувати захід")
def edit_event_start(message):
    cursor.execute("SELECT id, title FROM events")
    events = cursor.fetchall()

    text = "Оберіть ID заходу:\n"
    for e in events:
        text += f"{e[0]}. {e[1]}\n"

    bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(message, edit_event_title)

def edit_event_title(message):
    try:
        event_id = int(message.text)
        bot.send_message(message.chat.id, "Введіть нову назву заходу:")
        bot.register_next_step_handler(message, edit_event_date, event_id)
    except:
        bot.send_message(message.chat.id, "❌ Невірний ID")

def edit_event_date(message, event_id):
    title = message.text
    bot.send_message(message.chat.id, "Введіть нову дату:")
    bot.register_next_step_handler(message, edit_event_time, event_id, title)

def edit_event_time(message, event_id, title):
    date = message.text
    bot.send_message(message.chat.id, "Введіть новий час:")
    bot.register_next_step_handler(message, edit_event_location, event_id, title, date)

def edit_event_location(message, event_id, title, date):
    time = message.text
    bot.send_message(message.chat.id, "Введіть нове місце:")
    bot.register_next_step_handler(message, update_event, event_id, title, date, time)

def update_event(message, event_id, title, date, time):
    location = message.text
    cursor.execute("""
        UPDATE events
        SET title=?, date=?, time=?, location=?
        WHERE id=?
    """, (title, date, time, location, event_id))
    conn.commit()
    bot.send_message(message.chat.id, "✅ Захід оновлено")

# ---------- НАЗАД ----------
@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def back(message):
    bot.send_message(message.chat.id, "Головне меню", reply_markup=main_menu())

# ---------------- ЗАПУСК ----------------
bot.polling(none_stop=True)
