#!/usr/bin/env python3
# bot.py — Moment of Inertia Quiz Telegram Bot
# Uses: python-telegram-bot >= 20.0  (async)
# Run: python bot.py

import os
import logging
import asyncio
from typing import Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

from questions import QUESTIONS, SECTIONS, TOTAL_QUESTIONS, get_questions_by_section, get_question_by_id
import database as db

# ── CONFIGURATION ─────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS   = set(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
# Set ADMIN_IDS to your Telegram user ID(s), comma-separated

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── CONSTANTS ─────────────────────────────────────────
OPTION_LABELS = ["A", "B", "C", "D"]
SECTION_EMOJIS = {1:"📐", 2:"🔄", 3:"⚡", 4:"🔧", 5:"🕳️", 6:"🏆", 7:"🌀"}
GRADE_EMOJI = {
    range(0,  40):  "😔 Needs more practice",
    range(40, 60):  "📖 Keep studying!",
    range(60, 80):  "👍 Good effort!",
    range(80, 90):  "🌟 Great work!",
    range(90, 101): "🔥 Excellent! Outstanding!",
}

def grade_msg(pct):
    for r, msg in GRADE_EMOJI.items():
        if int(pct) in r:
            return msg
    return "Well done!"

# ── HELPERS ───────────────────────────────────────────
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def build_question_keyboard(q_index: int, session_id: int):
    """Build 4-option keyboard for a question."""
    q = QUESTIONS[q_index]
    buttons = []
    for i, (label, opt) in enumerate(zip(OPTION_LABELS, q["options"])):
        # Truncate option text for button if too long
        text = f"({label}) {opt[:40]}{'…' if len(opt)>40 else ''}"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"ans:{session_id}:{q['id']}:{label}"
        )])
    return InlineKeyboardMarkup(buttons)

def build_question_text(q_index: int, total: int, score: int) -> str:
    q = QUESTIONS[q_index]
    section_name = SECTIONS.get(q["section"], "")
    emoji = SECTION_EMOJIS.get(q["section"], "📝")

    options_text = "\n".join(
        f"  *({l})* {opt}"
        for l, opt in zip(OPTION_LABELS, q["options"])
    )

    return (
        f"{emoji} *Section {q['section']}: {section_name}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Q{q['id']} / {TOTAL_QUESTIONS}* \\| Score: {score}\n\n"
        f"{escape_md(q['text'])}\n\n"
        f"{options_text}"
    )

def escape_md(text: str) -> str:
    """Escape special MarkdownV2 characters."""
    special = r"\_*[]()~`>#+-=|{}.!"
    for ch in special:
        text = text.replace(ch, f"\\{ch}")
    return text

def format_results_text(score, total, pct, wrong_list) -> str:
    grade = grade_msg(pct)
    bar_filled = int(pct / 10)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)

    wrong_text = ""
    if wrong_list:
        wrong_ids = [str(a["question_id"]) for a in wrong_list[:10]]
        wrong_text = f"\n\n❌ *Missed:* Q{', Q'.join(wrong_ids)}"
        if len(wrong_list) > 10:
            wrong_text += f" ...and {len(wrong_list)-10} more"

    return (
        f"🎯 *Quiz Complete!*\n\n"
        f"Score: *{score}/{total}*\n"
        f"Accuracy: *{pct}%*\n"
        f"{bar}\n"
        f"{grade}"
        f"{wrong_text}"
    )

# ── COMMAND HANDLERS ──────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_student(user.id, user.username, user.first_name, user.last_name)

    student = db.get_student(user.id)
    if student and student["is_banned"]:
        await update.message.reply_text("⛔ You have been banned from this bot.")
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Start Full Quiz (150 Qs)", callback_data="quiz:0")],
        [
            InlineKeyboardButton("📐 Section 1", callback_data="quiz:1"),
            InlineKeyboardButton("🔄 Section 2", callback_data="quiz:2"),
        ],
        [
            InlineKeyboardButton("⚡ Section 3", callback_data="quiz:3"),
            InlineKeyboardButton("🔧 Section 4", callback_data="quiz:4"),
        ],
        [
            InlineKeyboardButton("🕳️ Section 5", callback_data="quiz:5"),
            InlineKeyboardButton("🏆 Section 6 (Tough)", callback_data="quiz:6"),
        ],
        [InlineKeyboardButton("🌀 Section 7", callback_data="quiz:7")],
        [
            InlineKeyboardButton("📊 My Stats", callback_data="mystats"),
            InlineKeyboardButton("🏅 Leaderboard", callback_data="leaderboard"),
        ],
        [InlineKeyboardButton("📄 Download Assignment", callback_data="download")],
    ])

    await update.message.reply_text(
        f"👋 Welcome, *{user.first_name}*\\!\n\n"
        f"🧲 *Moment of Inertia Quiz Bot*\n"
        f"📚 *150 Questions* across 7 sections\n\n"
        f"Topics covered:\n"
        f"• Basic shapes & formulae\n"
        f"• Parallel Axis Theorem \\(PAT\\)\n"
        f"• Perpendicular Axis Theorem \\(PPT\\)\n"
        f"• Composite bodies\n"
        f"• Removal of mass / cavities\n"
        f"• JEE Advanced level problems\n\n"
        f"Choose an option below to begin:",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=kb
    )

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Available Commands*\n\n"
        "/start \\- Main menu\n"
        "/quiz \\- Start full 150\\-question quiz\n"
        "/quiz\\_section \\<1\\-7\\> \\- Practice a specific section\n"
        "/stop \\- Stop current quiz session\n"
        "/score \\- Your current session score\n"
        "/mystats \\- Your overall statistics\n"
        "/leaderboard \\- Top students\n"
        "/download \\- Get the full assignment PDF\n\n"
        "*For Teachers / Admins:*\n"
        "/admin \\- Admin panel \\(admin only\\)\n"
        "/results \\- All student results \\(admin only\\)\n"
        "/broadcast \\<message\\> \\- Message all students \\(admin\\)\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

async def cmd_quiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_student(user.id, user.username, user.first_name, user.last_name)
    await start_quiz(update, ctx, user.id, section_filter=0)

async def cmd_quiz_section(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = ctx.args
    if not args or not args[0].isdigit() or not (1 <= int(args[0]) <= 7):
        await update.message.reply_text("Usage: /quiz_section <1-7>\nExample: /quiz_section 2")
        return
    section = int(args[0])
    db.upsert_student(user.id, user.username, user.first_name, user.last_name)
    await start_quiz(update, ctx, user.id, section_filter=section)

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = db.get_active_session(user.id)
    if not session:
        await update.message.reply_text("No active quiz session found.")
        return
    db.end_session(user.id)
    await update.message.reply_text(
        f"⏹ Quiz stopped\\.\n"
        f"Score at stop: *{session['score']}/{session['total_attempted']}*\n"
        f"Type /start to begin a new quiz\\.",
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def cmd_score(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = db.get_active_session(user.id)
    if not session:
        await update.message.reply_text("No active quiz session. Start one with /quiz")
        return
    total = session["total_attempted"]
    score = session["score"]
    pct = round(score / total * 100, 1) if total > 0 else 0
    await update.message.reply_text(
        f"📊 *Current Score*\n\n"
        f"Questions answered: {total}\n"
        f"Correct: {score}\n"
        f"Accuracy: {pct}%\n"
        f"Current Q: {session['current_q']}",
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def cmd_mystats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    stats = db.get_user_stats(user.id)
    lb = stats.get("leaderboard")

    best = f"Best: *{lb['best_score']} pts* \\({lb['best_pct']}%\\)" if lb else "No completed quiz yet"
    attempts = lb["attempts"] if lb else 0

    await update.message.reply_text(
        f"📈 *Your Statistics*\n\n"
        f"Total answers given: {stats['total_answers']}\n"
        f"Correct answers: {stats['correct']}\n"
        f"Overall accuracy: {stats['accuracy']}%\n"
        f"Quiz attempts: {attempts}\n"
        f"{best}",
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def cmd_leaderboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lb = db.get_leaderboard(10)
    if not lb:
        await update.message.reply_text("No results yet. Be the first to complete the quiz!")
        return

    lines = ["🏆 *Top Students — Leaderboard*\n"]
    medals = ["🥇", "🥈", "🥉"] + ["🎖️"] * 10
    for i, row in enumerate(lb):
        name = row.get("first_name") or row.get("username") or "Anonymous"
        lines.append(
            f"{medals[i]} {escape_md(name)} — "
            f"*{row['best_score']} pts* \\({row['best_pct']}%\\) | "
            f"{row['attempts']} attempt\\(s\\)"
        )
    await update.message.reply_text(
        "\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2
    )

async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only command.")
        return

    stats = db.get_overall_stats()
    hard_qs = db.get_hardest_questions(5)

    hard_text = ""
    for q in hard_qs:
        qdata = get_question_by_id(q["question_id"])
        q_preview = qdata["text"][:50] + "…" if qdata else "Unknown"
        hard_text += f"\n  Q{q['question_id']}: {q['accuracy']}% correct ({q['attempts']} attempts)"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 All Students", callback_data="admin:students")],
        [InlineKeyboardButton("📋 All Results", callback_data="admin:results")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin:broadcast")],
        [InlineKeyboardButton("🗑️ Clear DB (CAREFUL!)", callback_data="admin:cleardb")],
    ])

    await update.message.reply_text(
        f"🔐 *Admin Panel*\n\n"
        f"👥 Students registered: *{stats['total_students']}*\n"
        f"📝 Total sessions: *{stats['total_sessions']}*\n"
        f"✅ Completed: *{stats['completed_sessions']}*\n"
        f"🔢 Total answers: *{stats['total_answers']}*\n"
        f"🎯 Overall accuracy: *{stats['accuracy']}%*\n\n"
        f"🔥 Hardest Questions:{hard_text if hard_text else ' Not enough data yet'}",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=kb
    )

async def cmd_results(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    lb = db.get_leaderboard(50)
    if not lb:
        await update.message.reply_text("No results yet.")
        return

    lines = ["📋 *All Student Results*\n"]
    for row in lb:
        name = row.get("first_name") or row.get("username") or "Anonymous"
        lines.append(
            f"• {escape_md(name)} \\(ID: {row['user_id']}\\) — "
            f"{row['best_score']} pts, {row['best_pct']}%, {row['attempts']} tries"
        )

    # Split if too long
    full = "\n".join(lines)
    if len(full) > 4000:
        full = full[:4000] + "\n\\.\\.\\. truncated"

    await update.message.reply_text(full, parse_mode=ParseMode.MARKDOWN_V2)

async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /broadcast Your message here")
        return

    msg = " ".join(ctx.args)
    students = db.get_all_students()
    sent, failed = 0, 0

    for student in students:
        try:
            await ctx.bot.send_message(
                chat_id=student["user_id"],
                text=f"📢 *Message from your teacher:*\n\n{msg}",
                parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"✅ Broadcast sent to {sent} students. Failed: {failed}")

async def cmd_download(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Send the HTML assignment file
    html_path = "/mnt/user-data/outputs/MOI_Assignment.html"
    if os.path.exists(html_path):
        with open(html_path, "rb") as f:
            await update.message.reply_document(
                document=InputFile(f, filename="MOI_Assignment.html"),
                caption=(
                    "📄 *Moment of Inertia Assignment*\n"
                    "150 Questions — Open in any browser\n"
                    "Sections: Basics | PAT | PPT | Composite | Removal | JEE Adv."
                ),
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await update.message.reply_text(
            "📄 Assignment file not found on server. "
            "Please contact your teacher for the file."
        )

# ── QUIZ LOGIC ────────────────────────────────────────

async def start_quiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE, user_id: int, section_filter: int = 0):
    """Start a new quiz session."""
    student = db.get_student(user_id)
    if student and student["is_banned"]:
        msg = update.message or update.callback_query.message
        await msg.reply_text("⛔ You are banned from this quiz.")
        return

    # Create session
    session_id = db.create_session(user_id, section_filter)

    # Filter questions
    if section_filter == 0:
        quiz_questions = QUESTIONS
    else:
        quiz_questions = get_questions_by_section(section_filter)

    if not quiz_questions:
        msg = update.message or update.callback_query.message
        await msg.reply_text("No questions found for this section.")
        return

    # Store filtered question IDs in context
    ctx.user_data["session_id"] = session_id
    ctx.user_data["quiz_qs"] = [q["id"] for q in quiz_questions]
    ctx.user_data["q_ptr"] = 0
    ctx.user_data["score"] = 0
    ctx.user_data["total"] = len(quiz_questions)

    section_name = SECTIONS.get(section_filter, "All Sections") if section_filter else "All Sections"
    total = len(quiz_questions)

    msg = update.message or update.callback_query.message
    await msg.reply_text(
        f"🚀 *Quiz Started!*\n\n"
        f"Section: *{section_name}*\n"
        f"Questions: *{total}*\n\n"
        f"Select your answer using the buttons below\\.\n"
        f"Type /stop anytime to end the quiz\\.",
        parse_mode=ParseMode.MARKDOWN_V2
    )

    await send_question(update, ctx, 0, session_id, quiz_questions, 0)

async def send_question(update: Update, ctx: ContextTypes.DEFAULT_TYPE,
                        q_ptr: int, session_id: int, quiz_questions: list, score: int):
    """Send the question at index q_ptr."""
    if q_ptr >= len(quiz_questions):
        await finish_quiz(update, ctx, session_id, score, len(quiz_questions))
        return

    q = quiz_questions[q_ptr]
    q_index = next((i for i, x in enumerate(QUESTIONS) if x["id"] == q["id"]), 0)
    text = build_question_text(q_index, len(quiz_questions), score)
    keyboard = build_question_keyboard(q_index, session_id)

    msg = update.message or update.callback_query.message
    try:
        await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard)
    except Exception as e:
        # Fallback without MarkdownV2 if parsing fails
        await msg.reply_text(
            f"Q{q['id']}: {q['text']}\n\n" +
            "\n".join(f"({l}) {o}" for l, o in zip(OPTION_LABELS, q["options"])),
            reply_markup=keyboard
        )

async def finish_quiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE,
                      session_id: int, score: int, total: int):
    """Mark quiz complete and show results."""
    db.complete_session(session_id, score, total)

    user_id = update.effective_user.id
    db.update_leaderboard(user_id, score, total)

    # Get wrong answers from DB
    answers = db.get_session_answers(session_id)
    wrong = [a for a in answers if not a["is_correct"]]
    pct = round(score / total * 100, 1) if total > 0 else 0

    text = format_results_text(score, total, pct, wrong)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Retry Full Quiz", callback_data="quiz:0")],
        [InlineKeyboardButton("📊 My Stats",       callback_data="mystats")],
        [InlineKeyboardButton("🏅 Leaderboard",    callback_data="leaderboard")],
        [InlineKeyboardButton("🏠 Main Menu",      callback_data="menu")],
    ])

    msg = update.message or update.callback_query.message
    await msg.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

# ── CALLBACK QUERY HANDLER ───────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    data = query.data

    # ── START QUIZ ──
    if data.startswith("quiz:"):
        section = int(data.split(":")[1])
        db.upsert_student(user.id, user.username, user.first_name, user.last_name)
        await start_quiz(update, ctx, user.id, section)
        return

    # ── ANSWER ──
    if data.startswith("ans:"):
        _, session_id_str, q_id_str, chosen = data.split(":")
        session_id = int(session_id_str)
        q_id = int(q_id_str)

        # Validate this matches active session
        session = db.get_active_session(user.id)
        if not session or session["session_id"] != session_id:
            await query.edit_message_text("⚠️ Session expired. Start a new quiz with /quiz")
            return

        q = get_question_by_id(q_id)
        if not q:
            return

        correct = q["answer"]
        is_correct = db.record_answer(session_id, user.id, q_id, chosen, correct)

        # Get current context
        quiz_qs = ctx.user_data.get("quiz_qs", [x["id"] for x in QUESTIONS])
        q_ptr   = ctx.user_data.get("q_ptr", 0)
        score   = ctx.user_data.get("score", 0)

        if is_correct:
            score += 1
        q_ptr += 1

        ctx.user_data["q_ptr"] = q_ptr
        ctx.user_data["score"] = score

        db.update_session_progress(session_id, q_ptr + 1, score, q_ptr)

        # Show feedback
        if is_correct:
            feedback = f"✅ *Correct!*\n\n💡 {escape_md(q['explanation'][:300])}"
        else:
            feedback = (
                f"❌ *Wrong!* You chose *({chosen})*\n"
                f"✅ Correct answer: *({correct})*\n\n"
                f"💡 {escape_md(q['explanation'][:300])}"
            )

        try:
            await query.edit_message_text(feedback, parse_mode=ParseMode.MARKDOWN_V2)
        except Exception:
            await query.edit_message_text(
                f"{'✅ Correct!' if is_correct else f'❌ Wrong! Answer: ({correct})'}\n"
                f"Explanation: {q['explanation'][:300]}"
            )

        # Small delay then send next question
        await asyncio.sleep(1.5)

        # Get full quiz question list from session
        section_filter = session.get("section_filter", 0)
        if section_filter == 0:
            all_qs = QUESTIONS
        else:
            all_qs = get_questions_by_section(section_filter)

        if q_ptr >= len(all_qs):
            await finish_quiz(update, ctx, session_id, score, len(all_qs))
        else:
            await send_question(update, ctx, q_ptr, session_id, all_qs, score)
        return

    # ── MY STATS ──
    if data == "mystats":
        stats = db.get_user_stats(user.id)
        lb = stats.get("leaderboard")
        best = f"Best: *{lb['best_score']} pts* ({lb['best_pct']}%)" if lb else "No completed quiz yet"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back", callback_data="menu")]])
        await query.edit_message_text(
            f"📈 *Your Statistics*\n\n"
            f"Total answers: {stats['total_answers']}\n"
            f"Correct: {stats['correct']}\n"
            f"Accuracy: {stats['accuracy']}%\n"
            f"Attempts: {lb['attempts'] if lb else 0}\n"
            f"{best}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
        return

    # ── LEADERBOARD ──
    if data == "leaderboard":
        lb = db.get_leaderboard(10)
        lines = ["🏆 *Top Students*\n"]
        medals = ["🥇", "🥈", "🥉"] + ["🎖️"] * 10
        for i, row in enumerate(lb or []):
            name = row.get("first_name") or row.get("username") or "Anonymous"
            lines.append(f"{medals[i]} {name} — {row['best_score']} pts ({row['best_pct']}%)")
        if not lb:
            lines.append("No results yet!")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back", callback_data="menu")]])
        await query.edit_message_text(
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
        return

    # ── DOWNLOAD ──
    if data == "download":
        await query.edit_message_text("📄 Sending assignment file...")
        await cmd_download(update, ctx)
        return

    # ── MAIN MENU ──
    if data == "menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start Full Quiz (150 Qs)", callback_data="quiz:0")],
            [
                InlineKeyboardButton("📐 S1 Basics", callback_data="quiz:1"),
                InlineKeyboardButton("🔄 S2 PAT",    callback_data="quiz:2"),
            ],
            [
                InlineKeyboardButton("⚡ S3 PPT",    callback_data="quiz:3"),
                InlineKeyboardButton("🔧 S4 Composite", callback_data="quiz:4"),
            ],
            [
                InlineKeyboardButton("🕳️ S5 Removal", callback_data="quiz:5"),
                InlineKeyboardButton("🏆 S6 Tough",  callback_data="quiz:6"),
            ],
            [InlineKeyboardButton("🌀 S7 Mixed",    callback_data="quiz:7")],
            [
                InlineKeyboardButton("📊 My Stats",  callback_data="mystats"),
                InlineKeyboardButton("🏅 Top 10",    callback_data="leaderboard"),
            ],
        ])
        await query.edit_message_text(
            "🧲 *Moment of Inertia Quiz Bot*\n\nChoose a quiz to attempt:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
        return

    # ── ADMIN ACTIONS ──
    if data.startswith("admin:") and is_admin(user.id):
        action = data.split(":")[1]

        if action == "students":
            students = db.get_all_students()
            lines = [f"👥 *{len(students)} Registered Students*\n"]
            for s in students[:30]:
                name = s.get("first_name") or s.get("username") or "Anonymous"
                ban  = " 🚫" if s["is_banned"] else ""
                lines.append(f"• {name} (ID: {s['user_id']}){ban}")
            if len(students) > 30:
                lines.append(f"... and {len(students)-30} more")
            await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

        elif action == "results":
            lb = db.get_leaderboard(20)
            lines = ["📋 *Results Summary*\n"]
            for row in (lb or []):
                name = row.get("first_name") or row.get("username") or "Anon"
                lines.append(f"• {name}: {row['best_score']} pts, {row['best_pct']}%")
            await query.edit_message_text(
                "\n".join(lines) or "No results yet.",
                parse_mode=ParseMode.MARKDOWN
            )

        elif action == "broadcast":
            await query.edit_message_text(
                "To broadcast a message to all students, use:\n"
                "/broadcast Your message text here"
            )
        return

# ── ERROR HANDLER ─────────────────────────────────────
async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {ctx.error}", exc_info=True)

# ── MAIN ─────────────────────────────────────────────
def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Set your BOT_TOKEN in the environment variable or in bot.py")
        print("   export BOT_TOKEN='your_token_from_@BotFather'")
        print("   export ADMIN_IDS='your_telegram_user_id'")
        return

    print("🤖 Starting Moment of Inertia Quiz Bot...")
    print(f"   Questions loaded: {TOTAL_QUESTIONS}")
    print(f"   Admins: {ADMIN_IDS}")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Register handlers
    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("help",         cmd_help))
    app.add_handler(CommandHandler("quiz",         cmd_quiz))
    app.add_handler(CommandHandler("quiz_section", cmd_quiz_section))
    app.add_handler(CommandHandler("stop",         cmd_stop))
    app.add_handler(CommandHandler("score",        cmd_score))
    app.add_handler(CommandHandler("mystats",      cmd_mystats))
    app.add_handler(CommandHandler("leaderboard",  cmd_leaderboard))
    app.add_handler(CommandHandler("admin",        cmd_admin))
    app.add_handler(CommandHandler("results",      cmd_results))
    app.add_handler(CommandHandler("broadcast",    cmd_broadcast))
    app.add_handler(CommandHandler("download",     cmd_download))

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)

    print("✅ Bot is running! Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
