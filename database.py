# database.py — SQLite database for student progress and results

import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "moi_bot.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create all necessary tables."""
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            first_name  TEXT,
            last_name   TEXT,
            joined_at   TEXT,
            is_banned   INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sessions (
            session_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER,
            started_at      TEXT,
            completed_at    TEXT,
            current_q       INTEGER DEFAULT 1,
            score           INTEGER DEFAULT 0,
            total_attempted INTEGER DEFAULT 0,
            section_filter  INTEGER DEFAULT 0,
            is_active       INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES students(user_id)
        );

        CREATE TABLE IF NOT EXISTS answers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER,
            user_id     INTEGER,
            question_id INTEGER,
            chosen      TEXT,
            correct     TEXT,
            is_correct  INTEGER,
            answered_at TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS leaderboard (
            user_id     INTEGER PRIMARY KEY,
            best_score  INTEGER DEFAULT 0,
            best_pct    REAL DEFAULT 0.0,
            attempts    INTEGER DEFAULT 0,
            last_attempt TEXT,
            FOREIGN KEY(user_id) REFERENCES students(user_id)
        );
    """)
    conn.commit()
    conn.close()

# ── STUDENT ──────────────────────────────────────────
def upsert_student(user_id, username, first_name, last_name):
    conn = get_conn()
    conn.execute("""
        INSERT INTO students (user_id, username, first_name, last_name, joined_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username   = excluded.username,
            first_name = excluded.first_name,
            last_name  = excluded.last_name
    """, (user_id, username or "", first_name or "", last_name or "",
          datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_student(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM students WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_students():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM students ORDER BY joined_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def ban_student(user_id, ban=True):
    conn = get_conn()
    conn.execute("UPDATE students SET is_banned=? WHERE user_id=?", (1 if ban else 0, user_id))
    conn.commit()
    conn.close()

# ── SESSION ──────────────────────────────────────────
def create_session(user_id, section_filter=0):
    """Create a new quiz session. section_filter=0 means all sections."""
    # Deactivate any old sessions
    conn = get_conn()
    conn.execute("UPDATE sessions SET is_active=0 WHERE user_id=? AND is_active=1", (user_id,))
    conn.execute("""
        INSERT INTO sessions (user_id, started_at, current_q, score, section_filter, is_active)
        VALUES (?, ?, 1, 0, ?, 1)
    """, (user_id, datetime.now().isoformat(), section_filter))
    session_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return session_id

def get_active_session(user_id):
    conn = get_conn()
    row = conn.execute("""
        SELECT * FROM sessions WHERE user_id=? AND is_active=1
    """, (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_session_progress(session_id, current_q, score, total_attempted):
    conn = get_conn()
    conn.execute("""
        UPDATE sessions SET current_q=?, score=?, total_attempted=?
        WHERE session_id=?
    """, (current_q, score, total_attempted, session_id))
    conn.commit()
    conn.close()

def complete_session(session_id, score, total):
    conn = get_conn()
    conn.execute("""
        UPDATE sessions SET is_active=0, completed_at=?, score=?, total_attempted=?
        WHERE session_id=?
    """, (datetime.now().isoformat(), score, total, session_id))
    conn.commit()
    conn.close()

def end_session(user_id):
    conn = get_conn()
    conn.execute("UPDATE sessions SET is_active=0 WHERE user_id=? AND is_active=1", (user_id,))
    conn.commit()
    conn.close()

# ── ANSWERS ──────────────────────────────────────────
def record_answer(session_id, user_id, question_id, chosen, correct):
    is_correct = 1 if chosen == correct else 0
    conn = get_conn()
    conn.execute("""
        INSERT INTO answers (session_id, user_id, question_id, chosen, correct, is_correct, answered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (session_id, user_id, question_id, chosen, correct, is_correct, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return is_correct

def get_session_answers(session_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM answers WHERE session_id=? ORDER BY question_id", (session_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_answers(user_id, limit=150):
    conn = get_conn()
    rows = conn.execute("""
        SELECT a.*, s.started_at FROM answers a
        JOIN sessions s ON a.session_id = s.session_id
        WHERE a.user_id=?
        ORDER BY a.answered_at DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── LEADERBOARD ──────────────────────────────────────
def update_leaderboard(user_id, score, total):
    pct = round(score / total * 100, 1) if total > 0 else 0
    conn = get_conn()
    existing = conn.execute("SELECT * FROM leaderboard WHERE user_id=?", (user_id,)).fetchone()
    if existing:
        best_score = max(existing["best_score"], score)
        best_pct   = max(existing["best_pct"], pct)
        conn.execute("""
            UPDATE leaderboard SET best_score=?, best_pct=?, attempts=attempts+1, last_attempt=?
            WHERE user_id=?
        """, (best_score, best_pct, datetime.now().isoformat(), user_id))
    else:
        conn.execute("""
            INSERT INTO leaderboard (user_id, best_score, best_pct, attempts, last_attempt)
            VALUES (?, ?, ?, 1, ?)
        """, (user_id, score, pct, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_leaderboard(limit=10):
    conn = get_conn()
    rows = conn.execute("""
        SELECT l.*, s.first_name, s.username
        FROM leaderboard l
        JOIN students s ON l.user_id = s.user_id
        ORDER BY l.best_score DESC, l.best_pct DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── ADMIN STATS ───────────────────────────────────────
def get_overall_stats():
    conn = get_conn()
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM sessions WHERE is_active=0 AND completed_at IS NOT NULL").fetchone()[0]
    total_answers = conn.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
    correct_answers = conn.execute("SELECT COUNT(*) FROM answers WHERE is_correct=1").fetchone()[0]
    conn.close()
    return {
        "total_students": total_students,
        "total_sessions": total_sessions,
        "completed_sessions": completed,
        "total_answers": total_answers,
        "correct_answers": correct_answers,
        "accuracy": round(correct_answers / total_answers * 100, 1) if total_answers > 0 else 0
    }

def get_hardest_questions(limit=5):
    """Questions with lowest correct rate."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT question_id,
               COUNT(*) as attempts,
               SUM(is_correct) as correct,
               ROUND(SUM(is_correct)*100.0/COUNT(*), 1) as accuracy
        FROM answers
        GROUP BY question_id
        HAVING attempts >= 3
        ORDER BY accuracy ASC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_stats(user_id):
    conn = get_conn()
    sessions = conn.execute("SELECT * FROM sessions WHERE user_id=? ORDER BY started_at DESC", (user_id,)).fetchall()
    answers = conn.execute("SELECT COUNT(*) FROM answers WHERE user_id=?", (user_id,)).fetchone()[0]
    correct = conn.execute("SELECT COUNT(*) FROM answers WHERE user_id=? AND is_correct=1", (user_id,)).fetchone()[0]
    lb = conn.execute("SELECT * FROM leaderboard WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return {
        "sessions": [dict(s) for s in sessions],
        "total_answers": answers,
        "correct": correct,
        "accuracy": round(correct / answers * 100, 1) if answers > 0 else 0,
        "leaderboard": dict(lb) if lb else None
    }

# Initialise on import
init_db()
