import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

# Переменные из Railway
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
VIP_LINK = os.environ.get("VIP_LINK")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "Трейдер"
    
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

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("✅ Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
