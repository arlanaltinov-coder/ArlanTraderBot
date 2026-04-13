import os
import json
import logging
import psycopg
from psycopg.rows import dict_row
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _admin_id_raw = os.environ.get("ADMIN_ID")
    ADMIN_ID = int(_admin_id_raw) if _admin_id_raw else None
    is_admin = ADMIN_ID is not None and update.effective_user.id == ADMIN_ID

    text = (
        "📋 <b>ДОСТУПНЫЕ КОМАНДЫ:</b>\n\n"
        "👤 <b>Для всех:</b>\n"
        "/start - начать работу с ботом\n"
        "/help - показать эту справку\n"
    )

    if is_admin:
        text += (
            "\n🔐 <b>Только для администраторов:</b>\n"
            "/broadcast текст - отправить рассылку (старый способ)\n"
            "/users - показать всех подписчиков\n"
            "\n📝 <b>Система черновиков:</b>\n"
            "/draft_start - начать новый черновик (интерактивное меню)\n"
            "/draft_preview - предпросмотр текущего черновика\n"
            "/draft_send - отправить черновик всем подписчикам\n"
            "/drafts - история всех рассылок\n"
        )

    await update.message.reply_text(text, parse_mode="HTML")

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
    context.user_data.pop("waiting_for_photo", None)
    context.user_data.pop("waiting_for_text", None)
    context.user_data.pop("waiting_for_button", None)


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


def _draft_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню редактирования черновика."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Добавить текст", callback_data="draft_add_text"),
            InlineKeyboardButton("📸 Добавить фото", callback_data="draft_add_photo"),
        ],
        [
            InlineKeyboardButton("🔗 Добавить кнопку", callback_data="draft_add_button"),
            InlineKeyboardButton("👁️ Предпросмотр", callback_data="draft_preview"),
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="draft_cancel"),
        ],
    ])


def _draft_after_edit_keyboard() -> InlineKeyboardMarkup:
    """Кнопки после добавления контента — продолжить или предпросмотр."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Добавить текст", callback_data="draft_add_text"),
            InlineKeyboardButton("📸 Добавить фото", callback_data="draft_add_photo"),
        ],
        [
            InlineKeyboardButton("🔗 Добавить кнопку", callback_data="draft_add_button"),
            InlineKeyboardButton("👁️ Предпросмотр", callback_data="draft_preview"),
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="draft_cancel"),
        ],
    ])


def _draft_preview_keyboard() -> InlineKeyboardMarkup:
    """Кнопки под предпросмотром."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Отправить", callback_data="draft_send"),
            InlineKeyboardButton("✏️ Редактировать", callback_data="draft_edit_back"),
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="draft_cancel"),
        ],
    ])


async def _send_draft_preview(target, context: ContextTypes.DEFAULT_TYPE, draft: dict):
    """
    Отправляет предпросмотр черновика.
    target — объект с методами reply_text / reply_photo (Message или CallbackQuery.message).
    """
    reply_markup_content = _build_reply_markup(draft["buttons"])
    text = draft["text"] or ""

    await target.reply_text("👁️ <b>Предпросмотр рассылки:</b>", parse_mode="HTML")

    try:
        if draft["photo_file_id"]:
            await target.reply_photo(
                photo=draft["photo_file_id"],
                caption=text if text else None,
                parse_mode="HTML",
                reply_markup=reply_markup_content,
            )
        else:
            await target.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=reply_markup_content,
            )
    except Exception as e:
        await target.reply_text(f"❌ Ошибка предпросмотра: {e}")
        return

    btn_lines = "\n".join(
        f"  [{i+1}] {b['text']} → {b['url']}" for i, b in enumerate(draft["buttons"])
    )
    summary = (
        f"\n📊 <b>Состав черновика:</b>\n"
        f"• Текст: {'есть (' + str(len(text)) + ' симв.)' if text else 'нет'}\n"
        f"• Фото: {'есть' if draft['photo_file_id'] else 'нет'}\n"
        f"• Кнопки ({len(draft['buttons'])}):\n{btn_lines if btn_lines else '  нет'}\n\n"
        f"Что делаем дальше?"
    )
    await target.reply_text(
        summary,
        parse_mode="HTML",
        reply_markup=_draft_preview_keyboard(),
    )


async def _do_send_broadcast(
    context: ContextTypes.DEFAULT_TYPE,
    admin_id: int,
    draft: dict,
    reply_target,
):
    """Выполняет рассылку и обновляет БД. reply_target — Message для ответа."""
    subscribers = get_all_subscribers()
    if not subscribers:
        await reply_target.reply_text("❌ Нет подписчиков.")
        return

    try:
        db_id = _save_draft_to_db(admin_id, draft)
        draft["db_id"] = db_id
    except Exception as e:
        await reply_target.reply_text(f"❌ Не удалось сохранить в БД: {e}")
        return

    await reply_target.reply_text(
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

    await reply_target.reply_text(
        f"✅ Рассылка завершена (ID: {db_id})\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )


# ---------------------------------------------------------------------------
# /draft_start — начать новый черновик
# ---------------------------------------------------------------------------

async def draft_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return

    _clear_draft(context)

    # Создаём запись в БД сразу, чтобы иметь db_id
    draft = _get_draft(context)
    try:
        db_id = _save_draft_to_db(update.effective_user.id, draft)
        draft["db_id"] = db_id
    except Exception as e:
        await update.message.reply_text(f"❌ Не удалось создать черновик в БД: {e}")
        return

    await update.message.reply_text(
        "📝 <b>Новый черновик создан.</b> Отправляй сообщения:",
        parse_mode="HTML",
        reply_markup=_draft_menu_keyboard(),
    )


# ---------------------------------------------------------------------------
# /draft_preview — предпросмотр (команда)
# ---------------------------------------------------------------------------

async def draft_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return

    draft = _get_draft(context)

    if not draft["text"] and not draft["photo_file_id"]:
        await update.message.reply_text(
            "⚠️ Черновик пуст. Начни с /draft_start, затем добавь текст или фото.",
            reply_markup=_draft_menu_keyboard(),
        )
        return

    await _send_draft_preview(update.message, context, draft)


# ---------------------------------------------------------------------------
# /draft_send — отправить рассылку (команда)
# ---------------------------------------------------------------------------

async def draft_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return

    draft = _get_draft(context)

    if not draft["text"] and not draft["photo_file_id"]:
        await update.message.reply_text("⚠️ Черновик пуст. Нечего отправлять.")
        return

    await _do_send_broadcast(context, update.effective_user.id, draft, update.message)


# ---------------------------------------------------------------------------
# Обработчик входящих текстовых сообщений от админа (пока активен черновик)
# ---------------------------------------------------------------------------

async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принимает текст от админа когда черновик активен."""
    if not is_admin(update.effective_user.id):
        return

    # Режим ожидания текста для черновика
    if context.user_data.get("waiting_for_text"):
        context.user_data["waiting_for_text"] = False
        new_text = update.message.text or ""
        draft = _get_draft(context)

        if draft["text"]:
            draft["text"] += "\n" + new_text
        else:
            draft["text"] = new_text

        char_count = len(draft["text"])
        await update.message.reply_text(
            f"✅ Текст добавлен ({char_count} симв.).",
            reply_markup=_draft_after_edit_keyboard(),
        )
        return

    # Режим ожидания текста кнопки (формат "Текст|https://ссылка")
    if context.user_data.get("waiting_for_button"):
        context.user_data["waiting_for_button"] = False
        raw = (update.message.text or "").strip()

        if "|" not in raw:
            await update.message.reply_text(
                "❌ Неверный формат. Нужно: <b>Текст кнопки|https://ссылка</b>\n"
                "Попробуй ещё раз — нажми «🔗 Добавить кнопку».",
                parse_mode="HTML",
                reply_markup=_draft_after_edit_keyboard(),
            )
            return

        pipe_idx = raw.index("|")
        btn_text = raw[:pipe_idx].strip()
        btn_url = raw[pipe_idx + 1:].strip()

        if not btn_text or not btn_url:
            await update.message.reply_text(
                "❌ Текст и ссылка не могут быть пустыми.\n"
                "Попробуй ещё раз — нажми «🔗 Добавить кнопку».",
                reply_markup=_draft_after_edit_keyboard(),
            )
            return

        draft = _get_draft(context)
        draft["buttons"].append({"text": btn_text, "url": btn_url})

        await update.message.reply_text(
            f"✅ Кнопка добавлена: <b>{btn_text}</b> → {btn_url}\n"
            f"Всего кнопок: {len(draft['buttons'])}",
            parse_mode="HTML",
            reply_markup=_draft_after_edit_keyboard(),
        )
        return

    # Если черновик активен — добавляем текст автоматически
    if "current_draft" in context.user_data:
        new_text = update.message.text or ""
        draft = _get_draft(context)

        if draft["text"]:
            draft["text"] += "\n" + new_text
        else:
            draft["text"] = new_text

        char_count = len(draft["text"])
        await update.message.reply_text(
            f"✅ Текст добавлен ({char_count} симв.).",
            reply_markup=_draft_after_edit_keyboard(),
        )


# ---------------------------------------------------------------------------
# Обработчик входящих фото от админа (пока активен черновик)
# ---------------------------------------------------------------------------

async def admin_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принимает фото от админа когда черновик активен."""
    if not is_admin(update.effective_user.id):
        return

    if not context.user_data.get("waiting_for_photo") and "current_draft" not in context.user_data:
        return

    photo = update.message.photo[-1]  # наибольшее разрешение
    draft = _get_draft(context)
    draft["photo_file_id"] = photo.file_id
    context.user_data["waiting_for_photo"] = False

    await update.message.reply_text(
        "✅ Фото сохранено в черновик.",
        reply_markup=_draft_after_edit_keyboard(),
    )


# ---------------------------------------------------------------------------
# Обработчик нажатий на inline-кнопки черновика
# ---------------------------------------------------------------------------

async def draft_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.answer("❌ Нет прав.", show_alert=True)
        return

    data = query.data

    # ── Добавить текст ──────────────────────────────────────────────────────
    if data == "draft_add_text":
        context.user_data["waiting_for_text"] = True
        context.user_data["waiting_for_photo"] = False
        context.user_data["waiting_for_button"] = False
        await query.message.reply_text(
            "📝 Отправь текст следующим сообщением.\n"
            "Он будет добавлен к черновику."
        )

    # ── Добавить фото ───────────────────────────────────────────────────────
    elif data == "draft_add_photo":
        context.user_data["waiting_for_photo"] = True
        context.user_data["waiting_for_text"] = False
        context.user_data["waiting_for_button"] = False
        await query.message.reply_text(
            "📸 Отправь фото следующим сообщением."
        )

    # ── Добавить кнопку ─────────────────────────────────────────────────────
    elif data == "draft_add_button":
        context.user_data["waiting_for_button"] = True
        context.user_data["waiting_for_text"] = False
        context.user_data["waiting_for_photo"] = False
        await query.message.reply_text(
            "🔗 Отправь кнопку в формате:\n"
            "<b>Текст кнопки|https://ссылка</b>\n\n"
            "Пример: <code>Написать мне|https://t.me/username</code>",
            parse_mode="HTML",
        )

    # ── Предпросмотр ────────────────────────────────────────────────────────
    elif data == "draft_preview":
        draft = _get_draft(context)
        if not draft["text"] and not draft["photo_file_id"]:
            await query.message.reply_text(
                "⚠️ Черновик пуст. Сначала добавь текст или фото.",
                reply_markup=_draft_menu_keyboard(),
            )
            return
        await _send_draft_preview(query.message, context, draft)

    # ── Вернуться к редактированию ──────────────────────────────────────────
    elif data == "draft_edit_back":
        await query.message.reply_text(
            "✏️ Продолжай редактировать черновик:",
            reply_markup=_draft_menu_keyboard(),
        )

    # ── Отправить рассылку ──────────────────────────────────────────────────
    elif data == "draft_send":
        draft = _get_draft(context)
        if not draft["text"] and not draft["photo_file_id"]:
            await query.message.reply_text("⚠️ Черновик пуст. Нечего отправлять.")
            return
        await _do_send_broadcast(context, query.from_user.id, draft, query.message)

    # ── Отмена ──────────────────────────────────────────────────────────────
    elif data == "draft_cancel":
        draft = context.user_data.get("current_draft")
        db_id = draft.get("db_id") if draft else None
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
        await query.message.reply_text("🗑 Черновик отменён.")


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
    if len(text) > 4000:
        text = text[:4000] + "\n…(обрезано)"

    await update.message.reply_text(text, parse_mode="HTML")


def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("users", users))

    # Управление черновиками (команды)
    app.add_handler(CommandHandler("draft_start", draft_start))
    app.add_handler(CommandHandler("draft_preview", draft_preview))
    app.add_handler(CommandHandler("draft_send", draft_send))
    app.add_handler(CommandHandler("drafts", drafts_list))

    # Inline-кнопки черновика
    app.add_handler(CallbackQueryHandler(draft_callback_handler, pattern="^draft_"))

    # Входящие фото от админа (для черновика)
    app.add_handler(
        MessageHandler(filters.PHOTO & filters.User(list(ADMIN_IDS)), admin_photo_handler)
    )

    # Входящие текстовые сообщения от админа (для черновика)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.User(list(ADMIN_IDS)),
            admin_message_handler,
        )
    )

    print("✅ Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
