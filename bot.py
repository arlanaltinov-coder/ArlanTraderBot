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
    f"👋 Привет, <b>{name}</b>!\n\n"
    
    f"Добро пожаловать в <b>Arlan Trading</b> 📈\n\n"
    
    f"Меня зовут <b>Арлан Алтынов</b> — профессиональный трейдер с более чем 8-летним опытом торговли на Forex и CFD.\n"
    f"Специализируюсь на <b>Золоте (XAUUSD)</b> и помогаю трейдерам стабильно зарабатывать.\n\n"
    
    f"В канале ты найдёшь всё для успешной торговли:\n"
    f"• Точные торговые сигналы по Forex (с акцентом на Золото)\n"
    f"• Ежедневный технический и фундаментальный анализ рынка\n"
    f"• Обучающие материалы и разборы реальных сделок\n"
    f"• Полезные советы по работе с брокерами\n\n"
    
    f"🔥 <b>Для новичков</b> — провожу полноценное обучение с нуля: от основ трейдинга до уверенной торговли по моим сигналам.\n\n"
    
    f"💎 <b>VIP-группа — это премиум уровень:</b>\n"
    f"• До <b>12 премиум-сигналов</b> в месяц с высокой точностью\n"
    f"• Мои личные входы по Золоту и основным валютным парам\n"
    f"• Еженедельные розыгрыши с призами до <b>1000$</b>\n"
    f"• Бонусы к депозиту и эксклюзивные акции от брокеров\n"
    f"• Закрытые разборы рынка + личные ответы на вопросы\n\n"
    
    f"Я лично помогаю своим подписчикам выходить на стабильную прибыль. Многие уже успешно торгуют благодаря моим сигналам и поддержке.\n\n"
    
    f"<b>Хочешь зарабатывать на Золоте и Forex вместе со мной?</b>\n"
    f"Вступай в <b>VIP-группу</b> прямо сейчас 👇"
)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Вступить в VIP группу", url=VIP_LINK)],
        [InlineKeyboardButton("📢 Основной канал", url=CHANNEL_LINK)],
    ])
    
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_is_admin = is_admin(update.effective_user.id)

    text = (
        "📋 <b>ДОСТУПНЫЕ КОМАНДЫ:</b>\n\n"
        "👤 <b>Для всех:</b>\n"
        "/start - начать работу с ботом\n"
        "/help - показать эту справку\n"
    )

    if user_is_admin:
        text += (
            "\n🔐 <b>Только для администраторов:</b>\n"
            "/menu - панель управления рассылками\n"
            "/broadcast текст - отправить рассылку (быстрый способ)\n"
            "/users - показать всех подписчиков\n"
            "\n📝 <b>Система черновиков:</b>\n"
            "/draft_start - начать новый черновик\n"
            "/draft_preview - предпросмотр текущего черновика\n"
            "/draft_send - отправить черновик всем подписчикам\n"
            "/drafts - история всех рассылок\n"
            "\n💡 <b>Быстрый способ:</b> нажми «📝 Новая рассылка» в /menu,\n"
            "затем просто отправляй текст и фото — они добавятся автоматически.\n"
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
    """Возвращает текущий черновик из user_data"""
    if "current_draft" not in context.user_data:
        context.user_data["current_draft"] = {
            "text": "",
            "photo_file_id": None,
            "buttons": [],          # список кнопок: [{"text": "...", "url": "..."}]
            "db_id": None,
        }
    return context.user_data["current_draft"]


def _clear_draft(context: ContextTypes.DEFAULT_TYPE):
    """Очищает текущий черновик"""
    context.user_data.pop("current_draft", None)
    context.user_data.pop("draft_unsaved_changes", None)
    context.user_data.pop("waiting_for_button", None)
    
def _clear_draft(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("current_draft", None)
    context.user_data.pop("draft_unsaved_changes", None)
def _parse_buttons_from_text(text: str) -> tuple[str, list]:
    """Разбирает текст и автоматически вытаскивает кнопки формата:
    Название кнопки | https://ссылка"""
    lines = text.split("\n")
    clean_text = []
    buttons = []
    
    for line in lines:
        line = line.strip()
        if "|" in line:
            parts = [x.strip() for x in line.split("|", 1)]
            if len(parts) == 2 and (parts[1].startswith("http") or "t.me" in parts[1]):
                buttons.append({"text": parts[0], "url": parts[1]})
                continue        # эту строку пропускаем, она стала кнопкой
        clean_text.append(line)
    
    return "\n".join(clean_text).strip(), buttons

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


def _draft_keyboard() -> InlineKeyboardMarkup:
    """Единственная клавиатура для работы с черновиком."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👁️ Предпросмотр", callback_data="draft_preview"),
            InlineKeyboardButton("💾 Сохранить", callback_data="draft_save"),
        ],
        [
            InlineKeyboardButton("📤 Отправить", callback_data="draft_send"),
            InlineKeyboardButton("🔙 Главное меню", callback_data="draft_back_to_menu"),
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
        elif text:
            await target.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=reply_markup_content,
            )
        else:
            await target.reply_text("⚠️ Черновик пуст — нет ни текста, ни фото.")
    except Exception as e:
        await target.reply_text(f"❌ Ошибка предпросмотра: {e}")
        return

    await target.reply_text(
        "👆 Так будет выглядеть рассылка.",
        reply_markup=_draft_keyboard(),
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
        f"❌ Ошибок: {failed}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Главное меню", callback_data="menu_main")],
        ]),
    )


# ---------------------------------------------------------------------------
# Вспомогательные функции для меню управления рассылками
# ---------------------------------------------------------------------------

def _main_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню управления рассылками."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Новая рассылка", callback_data="menu_new_broadcast"),
            InlineKeyboardButton("📊 История", callback_data="menu_history_0"),
        ],
        [
            InlineKeyboardButton("👥 Подписчики", callback_data="menu_subscribers"),
            InlineKeyboardButton("🔧 Настройки", callback_data="menu_settings"),
        ],
    ])


def _get_broadcasts_page(page: int, per_page: int = 5) -> tuple[list, int]:
    """Возвращает страницу рассылок и общее количество."""
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM broadcasts")
                total = cur.fetchone()["cnt"]
                cur.execute(
                    """
                    SELECT id, status, created_at, sent_at, sent_count,
                           LEFT(text, 80) AS preview
                    FROM broadcasts
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (per_page, page * per_page),
                )
                rows = cur.fetchall()
        return rows, total
    except Exception as e:
        logger.error(f"❌ Ошибка получения рассылок: {e}")
        return [], 0


def _get_broadcast_by_id(broadcast_id: int) -> dict | None:
    """Возвращает рассылку по ID."""
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM broadcasts WHERE id = %s",
                    (broadcast_id,),
                )
                return cur.fetchone()
    except Exception as e:
        logger.error(f"❌ Ошибка получения рассылки: {e}")
        return None


def _delete_broadcast(broadcast_id: int) -> bool:
    """Удаляет черновик из БД. Возвращает True при успехе."""
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM broadcasts WHERE id = %s AND status = 'draft'",
                    (broadcast_id,),
                )
                deleted = cur.rowcount
            conn.commit()
        return deleted > 0
    except Exception as e:
        logger.error(f"❌ Ошибка удаления рассылки: {e}")
        return False


def _get_subscribers_stats() -> dict:
    """Возвращает статистику подписчиков."""
    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS total FROM subscribers")
                total = cur.fetchone()["total"]
                cur.execute(
                    """
                    SELECT user_id, username, first_name, joined_at
                    FROM subscribers
                    ORDER BY joined_at DESC
                    LIMIT 10
                    """
                )
                recent = cur.fetchall()
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM subscribers
                    WHERE joined_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                    """
                )
                week_count = cur.fetchone()["cnt"]
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM subscribers
                    WHERE joined_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                    """
                )
                month_count = cur.fetchone()["cnt"]
        return {
            "total": total,
            "recent": recent,
            "week": week_count,
            "month": month_count,
        }
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {e}")
        return {"total": 0, "recent": [], "week": 0, "month": 0}


def _history_keyboard(rows: list, page: int, total: int, per_page: int = 5) -> InlineKeyboardMarkup:
    """Строит клавиатуру для страницы истории рассылок."""
    buttons = []

    for r in rows:
        status_icon = "✅" if r["status"] == "sent" else "📝"
        created = r["created_at"].strftime("%d.%m %H:%M") if r["created_at"] else "—"
        label = f"{status_icon} #{r['id']} {created}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"menu_bc_detail_{r['id']}")])

    # Пагинация
    total_pages = (total + per_page - 1) // per_page
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Назад", callback_data=f"menu_history_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"menu_history_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("🔙 Главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(buttons)


def _broadcast_detail_keyboard(broadcast_id: int, status: str) -> InlineKeyboardMarkup:
    """Кнопки для детального просмотра рассылки."""
    rows = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"menu_bc_edit_{broadcast_id}")],
    ]
    if status == "draft":
        rows.append([
            InlineKeyboardButton("📤 Отправить", callback_data=f"menu_bc_send_{broadcast_id}"),
            InlineKeyboardButton("🗑 Удалить", callback_data=f"menu_bc_delete_confirm_{broadcast_id}"),
        ])
    rows.append([InlineKeyboardButton("🔙 К истории", callback_data="menu_history_0")])
    return InlineKeyboardMarkup(rows)


def _delete_confirm_keyboard(broadcast_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"menu_bc_delete_yes_{broadcast_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"menu_bc_detail_{broadcast_id}"),
        ],
    ])


# ---------------------------------------------------------------------------
# /menu — главное меню управления рассылками
# ---------------------------------------------------------------------------

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав.")
        return

    await update.message.reply_text(
        "📋 <b>УПРАВЛЕНИЕ РАССЫЛКАМИ</b>\n\n"
        "Выбери раздел:",
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(),
    )


# ---------------------------------------------------------------------------
# Обработчик inline-кнопок главного меню
# ---------------------------------------------------------------------------

async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.answer("❌ Нет прав.", show_alert=True)
        return

    data = query.data

    # ── Главное меню ────────────────────────────────────────────────────────
    if data == "menu_main":
        await query.message.reply_text(
            "📋 <b>УПРАВЛЕНИЕ РАССЫЛКАМИ</b>\n\n"
            "Выбери раздел:",
            parse_mode="HTML",
            reply_markup=_main_menu_keyboard(),
        )

    # ── Новая рассылка ──────────────────────────────────────────────────────
    elif data == "menu_new_broadcast":
        _clear_draft(context)
        draft = _get_draft(context)
        try:
            db_id = _save_draft_to_db(query.from_user.id, draft)
            draft["db_id"] = db_id
        except Exception as e:
            await query.message.reply_text(f"❌ Не удалось создать черновик: {e}")
            return
        await query.message.reply_text(
            "📝 Новый черновик. Отправляй текст и фото — они добавятся автоматически.",
            reply_markup=_draft_keyboard(),
        )

    # ── История рассылок (с пагинацией) ────────────────────────────────────
    elif data.startswith("menu_history_"):
        page = int(data.split("_")[-1])
        per_page = 5
        rows, total = _get_broadcasts_page(page, per_page)

        if not rows:
            await query.message.reply_text(
                "📋 Рассылок пока нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="menu_main")]
                ]),
            )
            return

        total_pages = (total + per_page - 1) // per_page
        text = (
            f"📊 <b>История рассылок</b> (стр. {page + 1}/{total_pages}, всего: {total}):\n\n"
        )
        for r in rows:
            status_icon = "✅" if r["status"] == "sent" else "📝"
            created = r["created_at"].strftime("%d.%m.%Y %H:%M") if r["created_at"] else "—"
            preview = (r["preview"] or "").replace("\n", " ")
            if len(preview) == 80:
                preview += "…"
            sent_info = ""
            if r["status"] == "sent" and r["sent_at"]:
                sent_info = f" | 📤 {r['sent_at'].strftime('%d.%m %H:%M')} ({r['sent_count']} польз.)"
            text += (
                f"{status_icon} <b>#{r['id']}</b> [{r['status']}] {created}{sent_info}\n"
                f"   {preview}\n\n"
            )

        await query.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=_history_keyboard(rows, page, total, per_page),
        )

    # ── Детали рассылки ─────────────────────────────────────────────────────
    elif data.startswith("menu_bc_detail_"):
        broadcast_id = int(data.split("_")[-1])
        bc = _get_broadcast_by_id(broadcast_id)
        if not bc:
            await query.message.reply_text("❌ Рассылка не найдена.")
            return

        status_icon = "✅" if bc["status"] == "sent" else "📝"
        created = bc["created_at"].strftime("%d.%m.%Y %H:%M") if bc["created_at"] else "—"
        preview = (bc["text"] or "").replace("\n", " ")
        if len(preview) > 200:
            preview = preview[:200] + "…"

        text = (
            f"{status_icon} <b>Рассылка #{bc['id']}</b>\n\n"
            f"📅 Создана: {created}\n"
            f"📌 Статус: {bc['status']}\n"
        )
        if bc["status"] == "sent" and bc["sent_at"]:
            text += (
                f"📤 Отправлена: {bc['sent_at'].strftime('%d.%m.%Y %H:%M')}\n"
                f"👥 Получателей: {bc['sent_count']}\n"
            )
        text += f"\n📝 Текст:\n{preview or '(нет текста)'}\n"
        if bc["photo_file_id"]:
            text += "🖼 Фото: есть\n"
        buttons_data = []
        if bc["buttons"]:
            try:
                buttons_data = json.loads(bc["buttons"])
            except Exception:
                pass
        if buttons_data:
            text += f"🔗 Кнопок: {len(buttons_data)}\n"

        await query.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=_broadcast_detail_keyboard(bc["id"], bc["status"]),
        )

    # ── Редактировать рассылку ──────────────────────────────────────────────
    elif data.startswith("menu_bc_edit_"):
        broadcast_id = int(data.split("_")[-1])
        bc = _get_broadcast_by_id(broadcast_id)
        if not bc:
            await query.message.reply_text("❌ Рассылка не найдена.")
            return

        _clear_draft(context)
        draft = _get_draft(context)

        buttons_data = []
        if bc["buttons"]:
            try:
                buttons_data = json.loads(bc["buttons"])
            except Exception:
                pass

        if bc["status"] == "draft":
            # Редактируем существующий черновик
            draft["text"] = bc["text"] or ""
            draft["photo_file_id"] = bc["photo_file_id"]
            draft["buttons"] = buttons_data
            draft["db_id"] = bc["id"]
            await query.message.reply_text(
                f"📝 Черновик #{bc['id']} загружен. Отправляй текст и фото — они добавятся автоматически.",
                reply_markup=_draft_keyboard(),
            )
        else:
            # Создаём новый черновик на основе отправленной рассылки
            draft["text"] = bc["text"] or ""
            draft["photo_file_id"] = bc["photo_file_id"]
            draft["buttons"] = buttons_data
            draft["db_id"] = None
            try:
                db_id = _save_draft_to_db(query.from_user.id, draft)
                draft["db_id"] = db_id
            except Exception as e:
                await query.message.reply_text(f"❌ Не удалось создать черновик: {e}")
                return
            await query.message.reply_text(
                f"📝 Новый черновик на основе рассылки #{bc['id']} (ID: #{draft['db_id']}). "
                "Отправляй текст и фото — они добавятся автоматически.",
                reply_markup=_draft_keyboard(),
            )

    # ── Отправить черновик из истории ───────────────────────────────────────
    elif data.startswith("menu_bc_send_"):
        broadcast_id = int(data.split("_")[-1])
        bc = _get_broadcast_by_id(broadcast_id)
        if not bc or bc["status"] != "draft":
            await query.message.reply_text("❌ Черновик не найден или уже отправлен.")
            return

        buttons_data = []
        if bc["buttons"]:
            try:
                buttons_data = json.loads(bc["buttons"])
            except Exception:
                pass

        draft = {
            "text": bc["text"] or "",
            "photo_file_id": bc["photo_file_id"],
            "buttons": buttons_data,
            "db_id": bc["id"],
        }
        context.user_data["current_draft"] = draft
        await _do_send_broadcast(context, query.from_user.id, draft, query.message)

    # ── Подтверждение удаления ──────────────────────────────────────────────
    elif data.startswith("menu_bc_delete_confirm_"):
        broadcast_id = int(data.split("_")[-1])
        bc = _get_broadcast_by_id(broadcast_id)
        if not bc or bc["status"] != "draft":
            await query.message.reply_text("❌ Можно удалять только черновики.")
            return
        await query.message.reply_text(
            f"⚠️ <b>Удалить черновик #{broadcast_id}?</b>\n\n"
            "Это действие необратимо.",
            parse_mode="HTML",
            reply_markup=_delete_confirm_keyboard(broadcast_id),
        )

    # ── Подтверждённое удаление ─────────────────────────────────────────────
    elif data.startswith("menu_bc_delete_yes_"):
        broadcast_id = int(data.split("_")[-1])
        success = _delete_broadcast(broadcast_id)
        if success:
            # Если удалённый черновик был активным — очищаем
            draft = context.user_data.get("current_draft")
            if draft and draft.get("db_id") == broadcast_id:
                _clear_draft(context)
            await query.message.reply_text(
                f"🗑 Черновик #{broadcast_id} удалён.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 К истории", callback_data="menu_history_0")],
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="menu_main")],
                ]),
            )
        else:
            await query.message.reply_text(
                "❌ Не удалось удалить. Возможно, черновик уже был удалён или отправлен.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 К истории", callback_data="menu_history_0")]
                ]),
            )

    # ── Подписчики ──────────────────────────────────────────────────────────
    elif data == "menu_subscribers":
        stats = _get_subscribers_stats()
        text = (
            f"👥 <b>Подписчики</b>\n\n"
            f"📊 Всего: <b>{stats['total']}</b>\n"
            f"📈 За последние 7 дней: <b>{stats['week']}</b>\n"
            f"📅 За последние 30 дней: <b>{stats['month']}</b>\n\n"
        )
        if stats["recent"]:
            text += "🕐 <b>Последние 10 подписчиков:</b>\n"
            for i, sub in enumerate(stats["recent"], 1):
                username = f"@{sub['username']}" if sub["username"] else "—"
                name = sub["first_name"] or "—"
                joined = sub["joined_at"].strftime("%d.%m.%Y %H:%M") if sub["joined_at"] else "—"
                text += f"{i}. {name} ({username}) — {joined}\n"
        else:
            text += "Подписчиков пока нет."

        await query.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Главное меню", callback_data="menu_main")]
            ]),
        )

    # ── Настройки ───────────────────────────────────────────────────────────
    elif data == "menu_settings":
        token = BOT_TOKEN or ""
        masked_token = token[:8] + "****" + token[-4:] if len(token) > 12 else "****"
        admin_ids_str = ", ".join(str(a) for a in sorted(ADMIN_IDS))
        text = (
            "🔧 <b>Настройки бота</b>\n\n"
            f"👤 <b>Администраторы:</b>\n{admin_ids_str}\n\n"
            f"🤖 <b>Токен бота:</b> <code>{masked_token}</code>\n\n"
            f"🗄 <b>База данных:</b> PostgreSQL\n"
            f"🔗 <b>VIP ссылка:</b> {'задана' if VIP_LINK else 'не задана'}\n"
            f"📢 <b>Канал:</b> {'задан' if CHANNEL_LINK else 'не задан'}\n"
        )
        await query.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Главное меню", callback_data="menu_main")]
            ]),
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
        "📝 Новый черновик. Отправляй текст и фото — они добавятся автоматически.",
        reply_markup=_draft_keyboard(),
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
            "⚠️ Черновик пуст. Начни с /draft_start, затем отправь текст или фото.",
            reply_markup=_draft_keyboard(),
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
    """Принимает текст от админа когда черновик активен — добавляет автоматически."""
    if not is_admin(update.effective_user.id):
        return

    if "current_draft" not in context.user_data:
        return

    new_text = update.message.text or ""
    draft = _get_draft(context)

    if draft["text"]:
        draft["text"] += "\n" + new_text
    else:
        draft["text"] = new_text

    context.user_data["draft_unsaved_changes"] = True
    char_count = len(draft["text"])
    await update.message.reply_text(
        f"✅ Текст добавлен ({char_count} символов)",
        reply_markup=_draft_keyboard(),
    )


# ---------------------------------------------------------------------------
# Обработчик входящих фото от админа (пока активен черновик)
# ---------------------------------------------------------------------------

async def admin_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принимает фото от админа когда черновик активен — добавляет автоматически."""
    if not is_admin(update.effective_user.id):
        return

    if "current_draft" not in context.user_data:
        return

    photo = update.message.photo[-1]  # наибольшее разрешение
    draft = _get_draft(context)
    draft["photo_file_id"] = photo.file_id
    context.user_data["draft_unsaved_changes"] = True

    await update.message.reply_text(
        "✅ Фото добавлено",
        reply_markup=_draft_keyboard(),
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

    # ── Предпросмотр ────────────────────────────────────────────────────────
    if data == "draft_preview":
        draft = _get_draft(context)
        if not draft["text"] and not draft["photo_file_id"]:
            await query.message.reply_text(
                "⚠️ Черновик пуст. Сначала отправь текст или фото.",
                reply_markup=_draft_keyboard(),
            )
            return
        await _send_draft_preview(query.message, context, draft)

    # ── Сохранить черновик ──────────────────────────────────────────────────
    elif data == "draft_save":
        draft = _get_draft(context)
        if not draft["text"] and not draft["photo_file_id"]:
            await query.message.reply_text(
                "⚠️ Черновик пуст — нечего сохранять.",
                reply_markup=_draft_keyboard(),
            )
            return
        try:
            db_id = _save_draft_to_db(query.from_user.id, draft)
            draft["db_id"] = db_id
            context.user_data["draft_unsaved_changes"] = False
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка сохранения: {e}")
            return
        await query.message.reply_text(
            "✅ Черновик сохранён",
            reply_markup=_draft_keyboard(),
        )

    # ── Отправить рассылку ──────────────────────────────────────────────────
    elif data == "draft_send":
        draft = _get_draft(context)
        if not draft["text"] and not draft["photo_file_id"]:
            await query.message.reply_text(
                "⚠️ Черновик пуст. Нечего отправлять.",
                reply_markup=_draft_keyboard(),
            )
            return
        await _do_send_broadcast(context, query.from_user.id, draft, query.message)

    # ── Главное меню (с проверкой несохранённых изменений) ──────────────────
    elif data == "draft_back_to_menu":
        has_unsaved = context.user_data.get("draft_unsaved_changes", False)
        draft = context.user_data.get("current_draft")
        has_content = draft and (draft.get("text") or draft.get("photo_file_id"))

        if has_content and has_unsaved:
            await query.message.reply_text(
                "⚠️ Есть несохранённые изменения. Сохранить черновик перед выходом?",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("💾 Сохранить и выйти", callback_data="draft_save_and_exit"),
                        InlineKeyboardButton("🗑 Выйти без сохранения", callback_data="draft_discard_and_exit"),
                    ],
                ]),
            )
        else:
            _clear_draft(context)
            await query.message.reply_text(
                "📋 <b>УПРАВЛЕНИЕ РАССЫЛКАМИ</b>\n\nВыбери раздел:",
                parse_mode="HTML",
                reply_markup=_main_menu_keyboard(),
            )

    # ── Сохранить и выйти ───────────────────────────────────────────────────
    elif data == "draft_save_and_exit":
        draft = _get_draft(context)
        try:
            db_id = _save_draft_to_db(query.from_user.id, draft)
            draft["db_id"] = db_id
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка сохранения: {e}")
            return
        _clear_draft(context)
        await query.message.reply_text(
            "✅ Черновик сохранён.\n\n📋 <b>УПРАВЛЕНИЕ РАССЫЛКАМИ</b>\n\nВыбери раздел:",
            parse_mode="HTML",
            reply_markup=_main_menu_keyboard(),
        )

    # ── Выйти без сохранения ────────────────────────────────────────────────
    elif data == "draft_discard_and_exit":
        _clear_draft(context)
        await query.message.reply_text(
            "📋 <b>УПРАВЛЕНИЕ РАССЫЛКАМИ</b>\n\nВыбери раздел:",
            parse_mode="HTML",
            reply_markup=_main_menu_keyboard(),
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

    # Панель управления рассылками
    app.add_handler(CommandHandler("menu", menu_command))

    # Управление черновиками (команды)
    app.add_handler(CommandHandler("draft_start", draft_start))
    app.add_handler(CommandHandler("draft_preview", draft_preview))
    app.add_handler(CommandHandler("draft_send", draft_send))
    app.add_handler(CommandHandler("drafts", drafts_list))

    # Inline-кнопки главного меню
    app.add_handler(CallbackQueryHandler(menu_callback_handler, pattern="^menu_"))

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
