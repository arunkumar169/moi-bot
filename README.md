# 🤖 Moment of Inertia Quiz — Telegram Bot

A fully-featured Telegram quiz bot for **150 Moment of Inertia MCQ questions** across 7 sections, designed for JEE/NEET Physics students.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📚 **150 Questions** | All 7 sections loaded automatically |
| 🗂️ **Section Filter** | Students can attempt full quiz or one section |
| ✅ **Instant Feedback** | Correct/wrong + explanation after each answer |
| 📊 **Progress Tracking** | Scores saved to SQLite database |
| 🏆 **Leaderboard** | Live top-10 student ranking |
| 📢 **Broadcast** | Teacher can message all students at once |
| 🔐 **Admin Panel** | View stats, students, results |
| 📄 **File Sharing** | Bot sends the assignment HTML file |
| 🚫 **Ban System** | Ban/unban individual students |

---

## 🚀 Setup — Step by Step

### Step 1: Get a Bot Token from Telegram

1. Open Telegram → search **@BotFather**
2. Send: `/newbot`
3. Choose a name: e.g. `MOI Physics Quiz`
4. Choose a username: e.g. `moi_physics_quiz_bot`
5. Copy the token: looks like `7123456789:AAHfiqksKZ8WXg...`

### Step 2: Get Your Telegram User ID (for admin)

1. Open Telegram → search **@userinfobot**
2. Send `/start`
3. It will reply with your **User ID** (a number like `987654321`)

### Step 3: Install Python & Dependencies

```bash
# Make sure Python 3.10+ is installed
python3 --version

# Install the library
pip install python-telegram-bot>=20.0
```

### Step 4: Set Environment Variables

**On Linux / Mac:**
```bash
export BOT_TOKEN="7123456789:AAHfiqksKZ8WXg..."
export ADMIN_IDS="987654321"          # Your Telegram user ID
```

**Multiple admins:**
```bash
export ADMIN_IDS="987654321,111222333,444555666"
```

**On Windows (Command Prompt):**
```cmd
set BOT_TOKEN=7123456789:AAHfiqksKZ8WXg...
set ADMIN_IDS=987654321
```

### Step 5: Run the Bot

```bash
# Navigate to the bot folder
cd moi_bot

# Run it
python3 bot.py
```

You should see:
```
🤖 Starting Moment of Inertia Quiz Bot...
   Questions loaded: 150
   Admins: {987654321}
✅ Bot is running! Press Ctrl+C to stop.
```

### Step 6: Share with Students

Send students your bot link:
```
https://t.me/moi_physics_quiz_bot
```

(Replace `moi_physics_quiz_bot` with your actual bot username)

---

## 📁 File Structure

```
moi_bot/
├── bot.py           ← Main bot file (run this)
├── questions.py     ← All 150 MOI questions
├── database.py      ← SQLite database manager
├── requirements.txt ← pip dependencies
├── README.md        ← This file
└── moi_bot.db       ← Created automatically on first run
```

---

## 🎓 Student Commands

| Command | Description |
|---|---|
| `/start` | Main menu with all options |
| `/quiz` | Start full 150-question quiz |
| `/quiz_section 2` | Practice only Section 2 (PAT) |
| `/stop` | End current quiz session |
| `/score` | Check current session score |
| `/mystats` | View personal statistics |
| `/leaderboard` | See top students |
| `/download` | Download the assignment file |
| `/help` | List all commands |

---

## 🔐 Teacher / Admin Commands

| Command | Description |
|---|---|
| `/admin` | Admin dashboard with stats |
| `/results` | All student scores |
| `/broadcast <msg>` | Send message to ALL students |

### Admin via Inline Buttons
The `/admin` command also shows buttons to:
- 👥 View all registered students
- 📋 View all results
- 📢 Broadcast instructions

---

## 🗂️ Sections Overview

| Section | Topics | Questions |
|---|---|---|
| 1 | Basic shapes & formulae | Q1–Q25 |
| 2 | Parallel Axis Theorem (PAT) | Q26–Q55 |
| 3 | Perpendicular Axis Theorem (PPT) | Q56–Q80 |
| 4 | Composite & Irregular Bodies | Q81–Q110 |
| 5 | Removal of Mass / Cavities | Q111–Q120 |
| 6 | JEE Advanced Tough Problems ★★★ | Q121–Q140 |
| 7 | Applications & Mixed | Q141–Q150 |

---

## 🖥️ Running as a Background Service (Linux)

To keep the bot running after you close the terminal:

```bash
# Option 1: using screen
screen -S moibot
python3 bot.py
# Press Ctrl+A then D to detach

# Option 2: using nohup
nohup python3 bot.py > bot.log 2>&1 &
echo "Bot PID: $!"

# Option 3: systemd service (most reliable)
sudo nano /etc/systemd/system/moibot.service
```

**systemd service file:**
```ini
[Unit]
Description=MOI Quiz Telegram Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/moi_bot
Environment="BOT_TOKEN=your_token_here"
Environment="ADMIN_IDS=your_user_id"
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable moibot
sudo systemctl start moibot
sudo systemctl status moibot
```

---

## 🌐 Hosting Options (Free)

| Platform | Instructions |
|---|---|
| **Railway.app** | Push code → set env vars → deploy |
| **Render.com** | Free tier available, set env vars |
| **PythonAnywhere** | Free plan, run as always-on task |
| **Your own VPS** | Use systemd service above |

For Railway/Render, set `BOT_TOKEN` and `ADMIN_IDS` as environment variables in their dashboard.

---

## 🔧 Customisation

### Add More Questions
Edit `questions.py` and add to the `QUESTIONS` list following the same format:
```python
{
    "id": 151,
    "section": 1,
    "text": "Your question here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer": "B",
    "explanation": "Because..."
}
```

### Change Admin IDs
Set `ADMIN_IDS` environment variable with comma-separated IDs:
```bash
export ADMIN_IDS="111111111,222222222"
```

### Randomise Question Order
In `bot.py`, in `start_quiz()`, add after building `quiz_questions`:
```python
import random
random.shuffle(quiz_questions)
```

---

## 📞 Troubleshooting

| Problem | Solution |
|---|---|
| `BOT_TOKEN not set` | Export the env variable before running |
| `ModuleNotFoundError` | Run `pip install python-telegram-bot>=20.0` |
| Bot not responding | Make sure the script is still running |
| `Conflict` error | You have 2 instances running; kill one |
| Questions not showing | Check questions.py has no syntax errors |

---

## 📜 License
Free for educational use. Built with ❤️ for Physics students.
