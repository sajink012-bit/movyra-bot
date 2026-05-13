# 🎬 MovYra Telegram Bot — Complete Setup Guide

A fully automated Telegram bot system for the **MovYra** movie website.
Handles promotional posting, group management, invite campaigns, daily content,
and website integration — all from a single Python process.

---

## 📁 File Structure

```
movyra_bot/
├── bot.py           ← Main bot: all command handlers & entry point
├── database.py      ← SQLite operations (promotions, groups, logs)
├── promotions.py    ← Build & send promo messages; round-robin picker
├── groups.py        ← Group & invite management helpers
├── scheduler.py     ← Auto-posting loop + daily content scheduler
├── config.py        ← Settings loaded from .env
├── templates.py     ← All formatted message templates (5 invite variants)
├── .env.example     ← Copy → .env and fill in your values
├── requirements.txt ← Python dependencies
└── backups/         ← Auto-created DB backups
```

---

## ✅ PART 1 — Create Your Telegram Bot

### Step 1: Get a Bot Token from @BotFather

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Enter a **name**: `MovYra Bot`
4. Enter a **username** (must end in `bot`): `movyra_official_bot`
5. BotFather sends you a token like:
   ```
   7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   Copy this — it's your `BOT_TOKEN`.

### Step 2: Customise Your Bot (also via BotFather)

Send these commands to @BotFather:

| Command | What to do |
|---|---|
| `/setdescription` | "Official bot for MovYra — movie reviews, OTT updates & more 🎬" |
| `/setabouttext` | "Get movie recommendations, promotions & join the MovYra community!" |
| `/setuserpic` | Upload your MovYra logo image |
| `/setcommands` | Paste the command list below |

**Paste this for `/setcommands`:**
```
start - Welcome & admin panel
addpromo - Add a new movie promotion
listpromos - View all promotions
editpromo - Edit a promotion: /editpromo [id] [field] [value]
deletepromo - Delete a promotion: /deletepromo [id]
broadcast - Send a promo to all groups now
pause - Pause auto-posting
resume - Resume auto-posting
setinterval - Change posting interval: /setinterval [minutes]
status - Bot status summary
addgroup - Add a group: /addgroup [id] [name]
removegroup - Remove a group: /removegroup [id]
listgroups - List all connected groups
setinvite - Set invite template (1-5)
sendinvite - Send invite to a group: /sendinvite [group_id]
movie - Search for a movie: /movie [name]
trending - Get trending movies
toprated - Get top-rated movies
help - Show all commands
```

### Step 3: Get Your Admin User ID

1. Message **@userinfobot** on Telegram
2. It will reply with your numeric ID like `123456789`
3. Save this — it's your `ADMIN_IDS` value

### Step 4: Get Your Group ID (if you have a community group)

1. Add **@userinfobot** to your group temporarily
2. Send any message in the group
3. The bot replies with the group's ID (negative number like `-1001234567890`)
4. Remove the bot after getting the ID

---

## ✅ PART 2 — Local Setup

### Requirements
- Python 3.9 or newer
- pip (comes with Python)

### Install Steps

```bash
# 1. Clone or download the movyra_bot folder
cd movyra_bot

# 2. Create a virtual environment (recommended)
python -m venv venv

# Activate it:
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your .env file
cp .env.example .env
# Now open .env in any text editor and fill in:
#   BOT_TOKEN   — from BotFather
#   ADMIN_IDS   — your Telegram user ID
#   MAIN_GROUP_ID — your community group ID (optional but recommended)

# 5. Run the bot
python bot.py
```

You should see output like:
```
2024-01-15 10:00:00 | INFO     | __main__ | Starting MovYra Bot v1.0.0 …
2024-01-15 10:00:00 | INFO     | database | Database initialised at movyra.db
2024-01-15 10:00:01 | INFO     | __main__ | Background tasks started.
```

---

## ✅ PART 3 — Add Your First Promotion

In Telegram, message your bot:

```
/addpromo
```

The bot walks you through 7 steps:
1. Movie title: `Manjummel Boys`
2. Description: `A gripping survival thriller based on true events from Kerala`
3. Rating: `8.4`
4. Genres: `#Thriller #Malayalam #Survival`
5. Website link: `https://movyra.com/manjummel-boys`
6. Trailer link: `https://youtube.com/watch?v=...` (or `/skip`)
7. Image URL: `https://movyra.com/posters/manjummel-boys.jpg` (or `/skip`)

---

## ✅ PART 4 — Add Promotion Groups

For each Telegram group you want to post in:

```
/addgroup -1009876543210 Telugu Movies Group
/addgroup -1001122334455 Malayalam Cinema Hub
```

The bot also **auto-detects** groups when you add it as a member — it registers them automatically.

---

## ✅ PART 5 — Deploy on PythonAnywhere (FREE, 24/7)

PythonAnywhere offers a **free tier** that can run a Python script 24/7.

### A. Create a Free Account
1. Go to [pythonanywhere.com](https://www.pythonanywhere.com)
2. Sign up for a **free Beginner account**

### B. Upload Your Files
1. Go to **Files** tab in PythonAnywhere dashboard
2. Create a new directory: `movyra_bot`
3. Upload all `.py` files and `requirements.txt`
   - Or use the **Bash console** to clone from GitHub (recommended)

```bash
# In PythonAnywhere Bash console:
git clone https://github.com/YOUR_USERNAME/movyra_bot.git
cd movyra_bot
```

### C. Install Dependencies

In the **Bash console**:
```bash
cd movyra_bot
pip3.10 install --user -r requirements.txt
```

### D. Set Environment Variables

Create your `.env` file:
```bash
nano .env
```
Paste your config (BOT_TOKEN, ADMIN_IDS, etc.) and save (`Ctrl+X → Y → Enter`).

### E. Run as an Always-On Task

**Free accounts** can use a workaround: Schedule a task every hour that restarts the bot if it's not running.

1. Go to **Tasks** tab
2. Add a new **Scheduled task** set to run every hour:
   ```bash
   cd /home/YOURUSERNAME/movyra_bot && python bot.py
   ```

**For reliable 24/7 uptime, upgrade to Hacker plan ($5/month)** which gives "Always-on tasks":
1. **Tasks** → **Always-on tasks**
2. Command: `python /home/YOURUSERNAME/movyra_bot/bot.py`
3. Click **Create**

### F. View Logs

```bash
# In Bash console:
tail -f /home/YOURUSERNAME/movyra_bot/movyra_bot.log
```

---

## ✅ PART 6 — Deploy on Render (FREE Alternative)

### A. Push Code to GitHub
```bash
git init
git add .
git commit -m "Initial MovYra bot"
git remote add origin https://github.com/YOUR_USERNAME/movyra_bot
git push -u origin main
```

**Important:** Add `.env` to `.gitignore` to avoid exposing your token:
```bash
echo ".env" >> .gitignore
echo "*.db" >> .gitignore
echo "backups/" >> .gitignore
```

### B. Create Render Service
1. Go to [render.com](https://render.com) → New → **Background Worker**
2. Connect your GitHub repository
3. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
4. Under **Environment** → Add all variables from your `.env` file
5. Click **Deploy**

---

## ✅ PART 7 — Deploy on Railway

1. Go to [railway.app](https://railway.app)
2. New Project → **Deploy from GitHub repo**
3. Add environment variables in the **Variables** tab
4. Railway auto-detects Python and runs `python bot.py`

---

## ✅ PART 8 — Website Integration

### Add "Join Telegram" Button to Your Website

Add this HTML anywhere in your website (header, footer, sidebar):

```html
<!-- MovYra Telegram Join Button -->
<a
  href="https://t.me/movyra"
  target="_blank"
  rel="noopener noreferrer"
  class="telegram-btn"
>
  <img src="https://telegram.org/favicon.ico" width="20" alt="Telegram">
  Join on Telegram
</a>

<style>
.telegram-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #229ED9;
  color: white;
  padding: 10px 20px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: bold;
  transition: background 0.2s;
}
.telegram-btn:hover { background: #1a7fb5; }
</style>
```

### Auto-Post New Reviews to Telegram (WordPress Example)

Add this to your `functions.php` or a custom plugin:

```php
function movyra_post_to_telegram($post_id) {
    // Only fire when a movie review is published
    $post = get_post($post_id);
    if ($post->post_type !== 'movie_review') return;
    if ($post->post_status !== 'publish') return;

    $bot_token = 'YOUR_BOT_TOKEN';
    $group_id  = 'YOUR_MAIN_GROUP_ID'; // e.g. -1001234567890
    $title     = get_the_title($post_id);
    $permalink = get_permalink($post_id);
    $excerpt   = get_the_excerpt($post_id);

    $text = "🎬 *New Review on MovYra!*\n\n*{$title}*\n\n{$excerpt}\n\n🔗 {$permalink}";

    wp_remote_post("https://api.telegram.org/bot{$bot_token}/sendMessage", [
        'body' => [
            'chat_id'    => $group_id,
            'text'       => $text,
            'parse_mode' => 'Markdown',
        ],
    ]);
}
add_action('publish_post', 'movyra_post_to_telegram');
```

### Website API for /movie, /trending, /toprated

The bot calls `WEBSITE_API_URL` for these commands. Expected response format:

**GET /api/movies/search?q=inception**
```json
{
  "results": [
    {
      "title": "Inception",
      "slug": "inception",
      "rating": "9.0",
      "year": "2010",
      "genres": "#SciFi #Thriller",
      "description": "A thief who steals corporate secrets through dream-sharing technology."
    }
  ]
}
```

**GET /api/movies/trending**
```json
{
  "results": [
    { "title": "Movie A", "rating": "9.2" },
    { "title": "Movie B", "rating": "8.8" }
  ]
}
```

---

## ✅ PART 9 — Main Community Group Setup

### Group Settings (do this in Telegram)

1. Create a new group: **"MovYra — Movie Updates & Reviews 🎬"**
2. Add your bot as **admin** (with permission to send messages & delete messages)
3. Set group type to **Public** and set a username like `@movyra`
4. Enable **Topics** in Group Settings (if available in your region)

### Pinned Message

Pin this message in your group:

```
📌 Welcome to MovYra Official Community! 🎬

🌐 Website: movyra.com
🤖 Bot: @movyra_official_bot

📋 RULES:
1. Be respectful to all members
2. No spam or self-promotion links
3. Movie topics only
4. Use the correct topic/category

📅 DAILY SCHEDULE:
🌅 9:00 AM — Movie of the Day
📈 2:00 PM — What's Trending
📺 6:00 PM — OTT Release Alert
🧠 8:00 PM — Movie Trivia

🔗 Topics:
📰 Movie News
🎬 Reviews
🎟️ OTT Updates
🎞️ Trailers
💬 Discussions
```

---

## 🔧 Useful Commands Cheatsheet

| Command | Description |
|---|---|
| `/status` | Check if bot is running, how many promos/groups |
| `/pause` | Stop auto-posting |
| `/resume` | Restart auto-posting |
| `/setinterval 60` | Post every 60 minutes |
| `/broadcast` | Send next promo immediately to all groups |
| `/addpromo` | Start 7-step promo wizard |
| `/listpromos` | See all promos with IDs |
| `/editpromo 3 rating 9.2` | Update rating of promo #3 |
| `/deletepromo 3` | Delete promo #3 |
| `/addgroup -100xxx GroupName` | Add a group manually |
| `/listgroups` | See all groups |
| `/setinvite 3` | Use OTT-focused invite template |
| `/sendinvite -100xxx` | Send invite to specific group |
| `/movie Oppenheimer` | Fetch movie info from website |
| `/trending` | Get trending list |
| `/toprated` | Get top-rated list |

---

## 🛡️ Security Notes

- **Never share your `.env` file or `BOT_TOKEN`**
- Add `.env` and `*.db` to `.gitignore` before pushing to GitHub
- Rotate your bot token if it gets leaked (via BotFather → `/revoke`)
- The bot rejects all admin commands from non-admin user IDs

---

## ❓ Troubleshooting

| Problem | Solution |
|---|---|
| Bot doesn't respond | Check `BOT_TOKEN` in `.env` is correct |
| Admin commands don't work | Check `ADMIN_IDS` matches your real user ID |
| Bot can't post to group | Make it an **admin** in the group |
| "Flood control exceeded" error | Increase `SEND_DELAY_SECONDS` in `config.py` |
| Database errors | Delete `movyra.db` and restart (re-runs init) |
| API calls fail | Check `WEBSITE_API_URL` is correct and returns JSON |

---

## 📞 Support

- Website: [movyra.com](https://movyra.com)
- Community: [t.me/movyra](https://t.me/movyra)
- Bot version: 1.0.0
