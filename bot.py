import os
import logging
import psycopg
from psycopg.rows import dict_row
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные из Railway
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
VIP_LINK = os.environ.get("VIP_LINK")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Инициализация БД
def init_db():
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS subscribers (
                        user_id BIGINT PRIMARY KEY,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {e}")

# Сохранение подписчика
def add_subscriber(user_id, username, first_name):
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO subscribers (user_id, username, first_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                """, (user_id, username, first_name))
            conn.commit()
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении: {e}")

# Получение всех подписчиков
def get_all_subscribers():
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM subscribers")
                subscribers = cur.fetchall()
        return [sub['user_id'] for sub in subscribers]
    except Exception as e:
        logger.error(f"❌ Ошибка при получении подписчиков: {e}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "Трейдер"
    
    # Сохраняем подписчика
    add_subscriber(user.id, user.username, user.first_name)
    
    text = (
        f"👋 Привет, {name}!\n\n"
        f"Добро пожаловать в <b>Arlan Trading</b> 📈\n\n"
        f"Здесь я публикую:\n"
        f"• Торговые сигналы по Forex\n"
        f"• Анализ рынка и новости\n"
        f"• Обучающие материалы\n\n"
        f"🔥 Хочешь эксклюзивные сигналы с высокой точностью?\n"
        f"Вступай в <b>VIP группу</b> 👇"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Вступить в VIP группу", url=VIP_LINK)],
        [InlineKeyboardButton("📢 Основной канал", url=CHANNEL_LINK)],
    ])
    
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Только для админа (твой ID)
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
    
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У тебя нет прав на рассылку")
        return
    
    if not context.args:
        await update.message.reply_text("📝 Использование: /broadcast текст рассылки")
        return
    
    message_text = " ".join(context.args)
    subscribers = get_all_subscribers()
    
    if not subscribers:
        await update.message.reply_text("❌ Нет подписчиков")
        return
    
    sent = 0
    failed = 0
    
    for user_id in subscribers:
        try:
            await context.bot.send_message(chat_id=user_id, text=message_text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            logger.error(f"Ошибка отправки {user_id}: {e}")
            failed += 1
    
    await update.message.reply_text(
        f"✅ Рассылка завершена\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    print("✅ Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
