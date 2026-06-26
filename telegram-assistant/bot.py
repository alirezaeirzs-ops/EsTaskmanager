import os
import logging
import asyncio
from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import Database
from ai_parser import parse_task_with_ai

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tehran")
REMINDER_MINUTES = int(os.getenv("REMINDER_MINUTES", "15"))
DAILY_SUMMARY_HOUR = int(os.getenv("DAILY_SUMMARY_HOUR", "8"))

db = Database()
tz = pytz.timezone(TIMEZONE)


# ─── /start ───────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.first_name)
    await update.message.reply_text(
        f"سلام {user.first_name} 👋\n\n"
        "من دستیار هوشمند شما هستم. می‌تونید تسک‌ها و برنامه‌های روزانه‌تون رو بهم بگید.\n\n"
        "📝 *نمونه پیام‌ها:*\n"
        "• «فردا ساعت ۱۰ جلسه با تیم دارم»\n"
        "• «امشب ساعت ۸ باید گزارش ماهانه بنویسم»\n"
        "• «هر روز ساعت ۷ صبح ورزش»\n\n"
        "📋 دستورات:\n"
        "/tasks — لیست تسک‌های امروز\n"
        "/all — همه تسک‌های فعال\n"
        "/done — علامت‌گذاری تسک انجام‌شده\n"
        "/delete — حذف تسک\n"
        "/settings — تنظیمات یادآوری\n"
        "/help — راهنما",
        parse_mode="Markdown"
    )


# ─── پردازش پیام متنی ─────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    msg = await update.message.reply_text("⏳ داریم پردازش می‌کنیم...")

    result = await parse_task_with_ai(text, ANTHROPIC_API_KEY, TIMEZONE)

    if not result or not result.get("tasks"):
        await msg.edit_text(
            "❓ نتونستم تسکی تشخیص بدم.\n"
            "لطفاً با ذکر زمان بنویسید، مثلاً:\n"
            "«فردا ساعت ۱۰ جلسه دارم»"
        )
        return

    saved = []
    for task in result["tasks"]:
        task_id = db.add_task(
            user_id=user.id,
            title=task["title"],
            due_datetime=task.get("due_datetime"),
            is_recurring=task.get("is_recurring", False),
            recurrence_rule=task.get("recurrence_rule"),
            reminder_minutes=task.get("reminder_minutes", REMINDER_MINUTES),
        )
        saved.append((task_id, task))

    # Build response
    lines = ["✅ *ذخیره شد!*\n"]
    for task_id, task in saved:
        due = task.get("due_datetime")
        time_str = ""
        if due:
            dt = datetime.fromisoformat(due).astimezone(tz)
            time_str = f" — {dt.strftime('%A %d %B ساعت %H:%M')}"
        recur = " 🔁" if task.get("is_recurring") else ""
        lines.append(f"• {task['title']}{time_str}{recur}")

    await msg.edit_text("\n".join(lines), parse_mode="Markdown")


# ─── /tasks — تسک‌های امروز ──────────────────────────────
async def tasks_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    tasks = db.get_tasks_in_range(user_id, start, end)
    if not tasks:
        await update.message.reply_text("📭 هیچ تسکی برای امروز ندارید.")
        return

    await update.message.reply_text(
        _format_task_list("📋 برنامه امروز:", tasks, tz),
        parse_mode="Markdown"
    )


# ─── /all — همه تسک‌ها ───────────────────────────────────
async def all_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = db.get_all_active_tasks(user_id)
    if not tasks:
        await update.message.reply_text("📭 هیچ تسک فعالی ندارید.")
        return

    await update.message.reply_text(
        _format_task_list("📋 همه تسک‌های فعال:", tasks, tz),
        parse_mode="Markdown"
    )


# ─── /done — انجام‌شده ────────────────────────────────────
async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = db.get_all_active_tasks(user_id)
    if not tasks:
        await update.message.reply_text("📭 هیچ تسک فعالی ندارید.")
        return

    keyboard = []
    for t in tasks:
        label = f"✅ {t['title']}"
        if t.get("due_datetime"):
            dt = datetime.fromisoformat(t["due_datetime"]).astimezone(tz)
            label += f" ({dt.strftime('%d/%m %H:%M')})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"done_{t['id']}")])

    await update.message.reply_text(
        "کدام تسک رو انجام دادید؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── /delete — حذف تسک ───────────────────────────────────
async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = db.get_all_active_tasks(user_id)
    if not tasks:
        await update.message.reply_text("📭 هیچ تسک فعالی ندارید.")
        return

    keyboard = []
    for t in tasks:
        label = f"🗑 {t['title']}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"del_{t['id']}")])

    await update.message.reply_text(
        "کدام تسک رو حذف کنم؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── /settings ────────────────────────────────────────────
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    reminder_min = user.get("reminder_minutes", REMINDER_MINUTES)

    keyboard = [
        [
            InlineKeyboardButton("۵ دقیقه", callback_data="set_rem_5"),
            InlineKeyboardButton("۱۰ دقیقه", callback_data="set_rem_10"),
            InlineKeyboardButton("۱۵ دقیقه", callback_data="set_rem_15"),
            InlineKeyboardButton("۳۰ دقیقه", callback_data="set_rem_30"),
        ]
    ]

    await update.message.reply_text(
        f"⚙️ *تنظیمات*\n\n"
        f"یادآوری فعلی: *{reminder_min} دقیقه* قبل از تسک\n\n"
        "تغییر زمان یادآوری:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── /help ────────────────────────────────────────────────
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *راهنمای ربات*\n\n"
        "*ثبت تسک:* کافیه متن بنویسید:\n"
        "• «فردا ساعت ۱۰ جلسه با مشتری»\n"
        "• «امشب ۸ شب گزارش بنویسم»\n"
        "• «هر دوشنبه ساعت ۹ تیم‌میتینگ»\n\n"
        "*دستورات:*\n"
        "/tasks — برنامه امروز\n"
        "/all — همه تسک‌های فعال\n"
        "/done — علامت‌گذاری انجام‌شده\n"
        "/delete — حذف تسک\n"
        "/settings — تنظیم زمان یادآوری\n\n"
        "*یادآوری‌ها:*\n"
        f"• {REMINDER_MINUTES} دقیقه قبل از هر تسک\n"
        f"• هر صبح ساعت {DAILY_SUMMARY_HOUR} خلاصه روز",
        parse_mode="Markdown"
    )


# ─── Callback Queries ─────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data.startswith("done_"):
        task_id = int(data.split("_")[1])
        db.mark_done(task_id, user_id)
        task = db.get_task(task_id)
        await query.edit_message_text(f"✅ *{task['title']}* انجام شد!", parse_mode="Markdown")

    elif data.startswith("del_"):
        task_id = int(data.split("_")[1])
        task = db.get_task(task_id)
        db.delete_task(task_id, user_id)
        await query.edit_message_text(f"🗑 *{task['title']}* حذف شد.", parse_mode="Markdown")

    elif data.startswith("set_rem_"):
        minutes = int(data.split("_")[2])
        db.update_user_reminder(user_id, minutes)
        await query.edit_message_text(f"✅ یادآوری روی *{minutes} دقیقه* قبل از تسک تنظیم شد.", parse_mode="Markdown")


# ─── Scheduler Jobs ───────────────────────────────────────
async def send_reminders(app: Application):
    """هر دقیقه اجرا می‌شه — تسک‌هایی که X دقیقه دیگه هستن رو یادآوری می‌کنه"""
    now = datetime.now(tz)
    tasks = db.get_upcoming_tasks_for_reminder(now)

    for task in tasks:
        try:
            dt = datetime.fromisoformat(task["due_datetime"]).astimezone(tz)
            mins_left = int((dt - now).total_seconds() / 60)
            await app.bot.send_message(
                chat_id=task["user_id"],
                text=(
                    f"⏰ *یادآوری*\n\n"
                    f"📌 {task['title']}\n"
                    f"🕐 ساعت {dt.strftime('%H:%M')} — {mins_left} دقیقه دیگه"
                ),
                parse_mode="Markdown"
            )
            db.mark_reminded(task["id"])
        except Exception as e:
            logger.error(f"Reminder error for task {task['id']}: {e}")


async def send_daily_summary(app: Application):
    """هر روز صبح خلاصه می‌فرسته"""
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    users = db.get_all_users()
    for user in users:
        tasks = db.get_tasks_in_range(user["user_id"], start, end)
        if not tasks:
            continue
        try:
            text = _format_task_list(
                f"🌅 صبح بخیر {user['name']}!\nبرنامه امروزت:",
                tasks, tz
            )
            await app.bot.send_message(
                chat_id=user["user_id"],
                text=text,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Daily summary error for user {user['user_id']}: {e}")


# ─── Helpers ──────────────────────────────────────────────
def _format_task_list(header: str, tasks: list, tz) -> str:
    lines = [f"*{header}*\n"]
    for t in tasks:
        status = "✅" if t.get("done") else "🔲"
        recur = " 🔁" if t.get("is_recurring") else ""
        due = ""
        if t.get("due_datetime"):
            dt = datetime.fromisoformat(t["due_datetime"]).astimezone(tz)
            due = f" — ساعت {dt.strftime('%H:%M')}"
        lines.append(f"{status} {t['title']}{due}{recur}")
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tasks", tasks_today))
    app.add_handler(CommandHandler("all", all_tasks))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Scheduler
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(send_reminders, "interval", minutes=1, args=[app])
    scheduler.add_job(
        send_daily_summary, "cron",
        hour=DAILY_SUMMARY_HOUR, minute=0, args=[app]
    )
    scheduler.start()

    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
