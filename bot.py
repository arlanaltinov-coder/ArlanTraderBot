import os
import json
import logging
import psycopg
from psycopg.rows import dict_row
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные из Railway
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
VIP_LINK = os.environ.get("VIP_LINK")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Список администраторов
ADMIN_IDS = {675675387, 8677862294}

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

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
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS broadcasts (
                        id SERIAL PRIMARY KEY,
                        admin_id BIGINT,
                        title VARCHAR(255),
                        text TEXT,
                        photo_file_id VARCHAR(255),
                        buttons TEXT,
                        status VARCHAR(50) DEFAULT 'draft',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        sent_at TIMESTAMP,
                        sent_count INT DEFAULT 0
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

# Получение всех подписчиков в виде форматированной строки
def get_all_subscribers_list():
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id, username, first_name, joined_at FROM subscribers ORDER BY joined_at ASC")
                subscribers = cur.fetchall()
        if not subscribers:
            return "📋 Подписчиков пока нет."
        lines = ["📋 Все подписчики:"]
        for i, sub in enumerate(subscribers, start=1):
            username = f"@{sub['username']}" if sub['username'] else "—"
            name = sub['first_name'] or "—"
            joined = sub['joined_at'].strftime("%Y-%m-%d %H:%M:%S") if sub['joined_at'] else "—"
            lines.append(f"{i}. user_id: {sub['user_id']}, username: {username}, name: {name}, joined: {joined}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"❌ Ошибка при получении списка подписчиков: {e}")
        return "❌ Ошибка при получении списка подписчиков."

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
    if not is_admin(update.effective_user.id):
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

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У тебя нет прав для просмотра подписчиков")
        return

    subscribers_list = get_all_subscribers_list()
    await update.message.reply_text(subscribers_list)


# ---------------------------------------------------------------------------
# Вспомогательные функции для работы с черновиками
# ---------------------------------------------------------------------------

def _get_draft(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Возвращает текущий черновик из user_data, создаёт пустой если нет."""
    if "current_draft" not in context.user_data:
        context.user_data["current_draft"] = {
            "text": "",
            "photo_file_id": None,
            "buttons": [],
            "db_id": None,
        }
    return context.user_data["current_draft"]


def _clear_draft(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("current_draft", None)


def _save_draft_to_db(admin_id: int, draft: dict) -> int:
    """Сохраняет черновик в БД и возвращает его id."""
    buttons_json = json.dumps(draft["buttons"], ensure_ascii=False)
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                if draft.get("db_id"):
                    cur.execute(
                        """
                        UPDATE broadcasts
                        SET text = %s, photo_file_id = %s, buttons = %s, status = 'draft'
                        WHERE id = %s
                        RETURNING id
                        """,
                        (draft["text"], draft["photo_file_id"], buttons_json, draft["db_id"]),
                    )
                    row = cur.fetchone()
                    db_id = row[0] if row else draft["db_id"]
                else:
                    cur.execute(
                        """
                        INSERT INTO broadcasts (admin_id, text, photo_file_id, buttons, status)
                        VALUES (%s, %s, %s, %s, 'draft')
                        RETURNING id
                        """,
                        (admin_id, draft["text"], draft["photo_file_id"], buttons_json),
                    )
                    db_id = cur.fetchone()[0]
            conn.commit()
        return db_id
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения черновика: {e}")
        raise


def _build_reply_markup(buttons: list) -> InlineKeyboardMarkup | None:
    """Строит InlineKeyboardMarkup из списка кнопок [{text, url}, ...]."""
    if not buttons:
        return None
    keyboard = [[InlineKeyboardButton(b["text"], url=b["url"])] for b in buttons]
    return InlineKeyboardMarkup(keyboard)


# ---------------------------------------------------------------------------
# /draft_start — начать новый черновик
# ---------------------------------------------------------------------------

async def draft_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return

    _clear_draft(context)
    _get_draft(context)  # создаём пустой
    await update.message.reply_text(
        "✏️ <b>Новый черновик создан.</b>\n\n"
        "Доступные команды:\n"
        "• /draft_text &lt;текст&gt; — добавить/дополнить текст\n"
        "• /draft_photo — отправь фото следующим сообщением\n"
        "• /draft_button Текст|https://ссылка — добавить кнопку\n"
        "• /draft_preview — предпросмотр\n"
        "• /draft_send — отправить всем подписчикам\n"
        "• /draft_delete — удалить черновик",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# /draft_text — добавить текст (многострочный, накапливается)
# ---------------------------------------------------------------------------

async def draft_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return

    # Берём весь текст после команды, включая переносы строк
    full_text = update.message.text or ""
    # Убираем первое слово-команду (/draft_text)
    parts = full_text.split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        await update.message.reply_text("📝 Использование: /draft_text ваш текст")
        return

    new_text = parts[1]
    draft = _get_draft(context)

    if draft["text"]:
        draft["text"] += "\n" + new_text
    else:
        draft["text"] = new_text

    char_count = len(draft["text"])
    await update.message.reply_text(
        f"✅ Текст добавлен. Всего символов: {char_count}\n"
        f"Используй /draft_text снова, чтобы дополнить, или /draft_preview для предпросмотра."
    )


# ---------------------------------------------------------------------------
# /draft_photo — ожидаем следующее фото от админа
# ---------------------------------------------------------------------------

async def draft_photo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return

    context.user_data["waiting_for_photo"] = True
    await update.message.reply_text("📷 Отправь фото следующим сообщением.")


async def draft_photo_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик входящих фото — сохраняет file_id в черновик."""
    if not is_admin(update.effective_user.id):
        return

    if not context.user_data.get("waiting_for_photo"):
        return

    photo = update.message.photo[-1]  # берём наибольшее разрешение
    draft = _get_draft(context)
    draft["photo_file_id"] = photo.file_id
    context.user_data["waiting_for_photo"] = False

    await update.message.reply_text(
        "✅ Фото сохранено в черновик.\n"
        "Используй /draft_preview для предпросмотра."
    )


# ---------------------------------------------------------------------------
# /draft_button Текст|https://ссылка — добавить кнопку
# ---------------------------------------------------------------------------

async def draft_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return

    full_text = update.message.text or ""
    parts = full_text.split(None, 1)
    if len(parts) < 2 or "|" not in parts[1]:
        await update.message.reply_text(
            "📝 Использование: /draft_button Текст кнопки|https://ссылка\n"
            "Пример: /draft_button НАПИСАТЬ|https://t.me/username"
        )
        return

    btn_part = parts[1].strip()
    pipe_idx = btn_part.index("|")
    btn_text = btn_part[:pipe_idx].strip()
    btn_url = btn_part[pipe_idx + 1:].strip()

    if not btn_text or not btn_url:
        await update.message.reply_text("❌ Текст и ссылка не могут быть пустыми.")
        return

    draft = _get_draft(context)
    draft["buttons"].append({"text": btn_text, "url": btn_url})

    total = len(draft["buttons"])
    await update.message.reply_text(
        f"✅ Кнопка добавлена: <b>{btn_text}</b> → {btn_url}\n"
        f"Всего кнопок: {total}",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# /draft_preview — предпросмотр черновика
# ---------------------------------------------------------------------------

async def draft_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return

    draft = _get_draft(context)

    if not draft["text"] and not draft["photo_file_id"]:
        await update.message.reply_text(
            "⚠️ Черновик пуст. Начни с /draft_start, затем добавь текст или фото."
        )
        return

    reply_markup = _build_reply_markup(draft["buttons"])
    text = draft["text"] or ""

    await update.message.reply_text("👁 <b>Предпросмотр рассылки:</b>", parse_mode="HTML")

    try:
        if draft["photo_file_id"]:
            await update.message.reply_photo(
                photo=draft["photo_file_id"],
                caption=text if text else None,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка предпросмотра: {e}")
        return

    btn_lines = "\n".join(
        f"  [{i+1}] {b['text']} → {b['url']}" for i, b in enumerate(draft["buttons"])
    )
    summary = (
        f"\n📊 <b>Состав черновика:</b>\n"
        f"• Текст: {'есть (' + str(len(text)) + ' симв.)' if text else 'нет'}\n"
        f"• Фото: {'есть' if draft['photo_file_id'] else 'нет'}\n"
        f"• Кнопки ({len(draft['buttons'])}):\n{btn_lines if btn_lines else '  нет'}\n\n"
        f"Готово? Отправь /draft_send"
    )
    await update.message.reply_text(summary, parse_mode="HTML")


# ---------------------------------------------------------------------------
# /draft_send — отправить рассылку всем подписчикам
# ---------------------------------------------------------------------------

async def draft_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return

    draft = _get_draft(context)

    if not draft["text"] and not draft["photo_file_id"]:
        await update.message.reply_text("⚠️ Черновик пуст. Нечего отправлять.")
        return

    subscribers = get_all_subscribers()
    if not subscribers:
        await update.message.reply_text("❌ Нет подписчиков.")
        return

    # Сохраняем черновик в БД перед отправкой
    try:
        db_id = _save_draft_to_db(update.effective_user.id, draft)
        draft["db_id"] = db_id
    except Exception as e:
        await update.message.reply_text(f"❌ Не удалось сохранить в БД: {e}")
        return

    await update.message.reply_text(
        f"🚀 Начинаю рассылку для {len(subscribers)} подписчиков..."
    )

    reply_markup = _build_reply_markup(draft["buttons"])
    text = draft["text"] or ""
    sent = 0
    failed = 0

    for user_id in subscribers:
        try:
            if draft["photo_file_id"]:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=draft["photo_file_id"],
                    caption=text if text else None,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            sent += 1
        except Exception as e:
            logger.error(f"Ошибка отправки {user_id}: {e}")
            failed += 1

    # Обновляем статус в БД
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE broadcasts
                    SET status = 'sent', sent_at = CURRENT_TIMESTAMP, sent_count = %s
                    WHERE id = %s
                    """,
                    (sent, db_id),
                )
            conn.commit()
    except Exception as e:
        logger.error(f"❌ Ошибка обновления статуса рассылки: {e}")

    _clear_draft(context)

    await update.message.reply_text(
        f"✅ Рассылка завершена (ID: {db_id})\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )


# ---------------------------------------------------------------------------
# /draft_delete — удалить текущий черновик (из памяти и БД если сохранён)
# ---------------------------------------------------------------------------

async def draft_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return

    draft = context.user_data.get("current_draft")
    if not draft:
        await update.message.reply_text("⚠️ Активного черновика нет.")
        return

    db_id = draft.get("db_id")
    if db_id:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM broadcasts WHERE id = %s AND status = 'draft'",
                        (db_id,),
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка удаления черновика из БД: {e}")

    _clear_draft(context)
    await update.message.reply_text("🗑 Черновик удалён.")


# ---------------------------------------------------------------------------
# /draft_edit <id> — загрузить отправленную/сохранённую рассылку для редактирования
# ---------------------------------------------------------------------------

async def draft_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("📝 Использование: /draft_edit <id>")
        return

    broadcast_id = int(context.args[0])

    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM broadcasts WHERE id = %s",
                    (broadcast_id,),
                )
                row = cur.fetchone()
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка БД: {e}")
        return

    if not row:
        await update.message.reply_text(f"❌ Рассылка #{broadcast_id} не найдена.")
        return

    buttons = []
    if row["buttons"]:
        try:
            buttons = json.loads(row["buttons"])
        except json.JSONDecodeError:
            buttons = []

    _clear_draft(context)
    draft = _get_draft(context)
    draft["text"] = row["text"] or ""
    draft["photo_file_id"] = row["photo_file_id"]
    draft["buttons"] = buttons
    draft["db_id"] = row["id"]

    await update.message.reply_text(
        f"✏️ Рассылка <b>#{broadcast_id}</b> загружена для редактирования.\n\n"
        f"• Текст: {'есть (' + str(len(draft['text'])) + ' симв.)' if draft['text'] else 'нет'}\n"
        f"• Фото: {'есть' if draft['photo_file_id'] else 'нет'}\n"
        f"• Кнопок: {len(draft['buttons'])}\n\n"
        f"Используй /draft_text, /draft_photo, /draft_button для изменений,\n"
        f"затем /draft_preview и /draft_send для повторной отправки.",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# /drafts — список всех черновиков и отправленных рассылок
# ---------------------------------------------------------------------------

async def drafts_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return

    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, status, created_at, sent_at, sent_count,
                           LEFT(text, 60) AS preview
                    FROM broadcasts
                    ORDER BY created_at DESC
                    LIMIT 30
                    """
                )
                rows = cur.fetchall()
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка БД: {e}")
        return

    if not rows:
        await update.message.reply_text("📋 Рассылок пока нет.")
        return

    lines = ["📋 <b>История рассылок:</b>\n"]
    for r in rows:
        status_icon = "✅" if r["status"] == "sent" else "📝"
        created = r["created_at"].strftime("%d.%m.%Y %H:%M") if r["created_at"] else "—"
        sent_info = ""
        if r["status"] == "sent":
            sent_at = r["sent_at"].strftime("%d.%m.%Y %H:%M") if r["sent_at"] else "—"
            sent_info = f" | отправлено: {sent_at} ({r['sent_count']} польз.)"
        preview = (r["preview"] or "").replace("\n", " ")
        if len(preview) == 60:
            preview += "…"
        lines.append(
            f"{status_icon} <b>#{r['id']}</b> [{r['status']}] {created}{sent_info}\n"
            f"   {preview}"
        )

    text = "\n\n".join(lines)
    # Telegram limit 4096 chars
    if len(text) > 4000:
        text = text[:4000] + "\n…(обрезано)"

    await update.message.reply_text(text, parse_mode="HTML")


def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("users", users))

    # Управление черновиками
    app.add_handler(CommandHandler("draft_start", draft_start))
    app.add_handler(CommandHandler("draft_text", draft_text))
    app.add_handler(CommandHandler("draft_photo", draft_photo_cmd))
    app.add_handler(CommandHandler("draft_button", draft_button))
    app.add_handler(CommandHandler("draft_preview", draft_preview))
    app.add_handler(CommandHandler("draft_send", draft_send))
    app.add_handler(CommandHandler("draft_delete", draft_delete))
    app.add_handler(CommandHandler("draft_edit", draft_edit))
    app.add_handler(CommandHandler("drafts", drafts_list))

    # Обработчик входящих фото (для /draft_photo)
    app.add_handler(
        MessageHandler(filters.PHOTO & filters.User(list(ADMIN_IDS)), draft_photo_receive)
    )

    print("✅ Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
