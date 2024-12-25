from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, ContextTypes
import sqlite3
import random

# Константы для этапов диалога
DATE_START, DATE_END, GUESTS, ROOM_TYPE = range(4)

# Создание приложения Telegram
app = ApplicationBuilder().token("7503355405:AAHvGPzFIkZ9SdAnxhHySbrhD07sDw7DssI").build()

# Настройка базы данных
def setup_database():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        chat_id INTEGER NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date_start TEXT NOT NULL,
        date_end TEXT NOT NULL,
        guests INTEGER NOT NULL,
        room_type TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    connection.commit()
    connection.close()

setup_database()

# Функция для добавления пользователя
def add_user(username, chat_id):
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO users (username, chat_id)
        VALUES (?, ?)
        """, (username, chat_id))
        connection.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при добавлении пользователя: {e}")
    finally:
        connection.close()

# Команда /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Анекдоты", callback_data="a")],
        [InlineKeyboardButton("Меню", callback_data="menu")],
        [InlineKeyboardButton("Донат", callback_data="donat")],
        [InlineKeyboardButton("Все фото", callback_data="foto")],
        [InlineKeyboardButton("Забронировать", callback_data="book")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Добро пожаловать! Выберите действие:", reply_markup=reply_markup)

# Обработка кнопок
async def tap_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "a":
        random_joke = random.choice([
            "Покупайте батарейки «сынок президента». Батарейки «сынок президента» — не сядет никогда!",
            "Десять тысяч мужчин разного возраста ответили на вопрос: «Если бы у вас был выбор между новым автомобилем и идеальной женщиной, что бы вы выбрали?» Ответы: — дизель 57%, — бензин 43%.",
            "Надпись в сортире: НЕ ССЫ, ПРОРВЕМСЯ!",
            "— Ты считаешь, что шутить про то, что в Африке нет воды это смешно? — Ни капельки.",
            "— Официант, а почему у меня в супе слуховой аппарат?! — Простите, что вы сказали?"
        ])
        await query.message.reply_text(f"Анекдот: {random_joke}")
    elif query.data == "menu":
        await query.message.reply_text("Меню скоро будет доступно!")
    elif query.data == "donat":
        await query.message.reply_text("На булочку: 4441111137101667")
    elif query.data == "foto":
        # Пример отправки фотографий
        photo_paths = ["food1.jpg", "me.jpg", "no.jpg"]
        try:
            media_group = [InputMediaPhoto(open(photo, "rb")) for photo in photo_paths]
            await query.message.reply_media_group(media_group)
        except FileNotFoundError:
            await query.message.reply_text("Ошибка: фотографии не найдены.")
    elif query.data == "book":
        await query.message.reply_text("Введите дату заезда (например, 2023-12-25):")
        return DATE_START

# Шаги для бронирования
async def date_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['date_start'] = update.message.text
    await update.message.reply_text("Введите дату выезда (например, 2023-12-30):")
    return DATE_END

async def date_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['date_end'] = update.message.text
    await update.message.reply_text("Сколько гостей будет?")
    return GUESTS

async def guests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['guests'] = update.message.text
    reply_keyboard = [["Одноместный", "Двухместный", "Семейный"]]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите тип комнаты:", reply_markup=reply_markup)
    return ROOM_TYPE

async def room_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_user.id
    context.user_data['room_type'] = update.message.text

    add_booking(
        chat_id,
        context.user_data['date_start'],
        context.user_data['date_end'],
        context.user_data['guests'],
        context.user_data['room_type']
    )

    booking_details = (
        f"Ваши данные для бронирования:\n"
        f"- Дата заезда: {context.user_data['date_start']}\n"
        f"- Дата выезда: {context.user_data['date_end']}\n"
        f"- Количество гостей: {context.user_data['guests']}\n"
        f"- Тип номера: {context.user_data['room_type']}\n"
        "Если все верно, наш администратор свяжется с вами для подтверждения."
    )
    await update.message.reply_text(booking_details, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бронирование отменено. Возвращайтесь, когда будете готовы!",
                                    reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Обработчик ConversationHandler
booking_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(tap_button)],
    states={
        DATE_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_start)],
        DATE_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_end)],
        GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, guests)],
        ROOM_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, room_type)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Регистрация обработчиков
app.add_handler(CommandHandler("start", start_command))
app.add_handler(booking_handler)

# Запуск приложения
if __name__ == "__main__":
    app.run_polling()
