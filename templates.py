"""
templates.py - MovYra Bot Message Templates
============================================
All formatted Telegram messages live here.
Uses HTML parse mode throughout (supported by python-telegram-bot v20+).

Invite templates rotate so the same groups don't always see the same message.
"""

import config


# ─── PROMOTION CARD ───────────────────────────────────────────────────────────

def build_promo_message(promo: dict) -> str:
    """
    Build the HTML-formatted promotion message from a promotion row.
    `promo` can be a sqlite3.Row or any dict-like object.
    """
    genres = promo["genres"] or ""
    rating = promo["rating"] or "N/A"

    return (
        f"🎬 <b>{promo['title']}</b>\n\n"
        f"⭐ <b>Rating:</b> {rating}/10\n\n"
        f"📝 {promo['description']}\n\n"
        f"🏷️ {genres}\n\n"
        f"🔗 <a href='{promo['website_link']}'>Read More on MovYra</a>"
    )


# ─── INVITE TEMPLATES (5 variants) ────────────────────────────────────────────

INVITE_TEMPLATES = [

    # 1 — Movie Lover
    (
        "🎬 <b>Movie lovers, this one's for you!</b>\n\n"
        "Join <b>MovYra — Movie Updates & Reviews</b> 🍿\n\n"
        "✅ Latest movie releases\n"
        "✅ Honest reviews & ratings\n"
        "✅ Exclusive trailers & clips\n"
        "✅ Box-office buzz & predictions\n\n"
        f"👉 <a href='{config.MAIN_GROUP_LINK}'>Join MovYra Community</a>\n\n"
        "🌐 movyra.com"
    ),

    # 2 — Review / Discussion
    (
        "💬 <b>Love discussing movies?</b>\n\n"
        "Join <b>MovYra</b> — where movie talks never stop! 🎭\n\n"
        "🎯 Deep-dive reviews\n"
        "🎯 Director & actor spotlights\n"
        "🎯 Weekly movie polls\n"
        "🎯 Fan theories & hidden details\n\n"
        f"👉 <a href='{config.MAIN_GROUP_LINK}'>Join the Discussion</a>\n\n"
        "🌐 movyra.com"
    ),

    # 3 — OTT Updates
    (
        "📺 <b>Never miss a streaming release again!</b>\n\n"
        "Join <b>MovYra</b> for all OTT updates 🎥\n\n"
        "🔔 Netflix, Prime, Disney+, Hotstar & more\n"
        "🔔 Weekly OTT calendar\n"
        "🔔 Hidden gems you must watch\n"
        "🔔 Platform-exclusive content alerts\n\n"
        f"👉 <a href='{config.MAIN_GROUP_LINK}'>Get OTT Alerts</a>\n\n"
        "🌐 movyra.com"
    ),

    # 4 — Regional Cinema (Malayalam / Tamil / Hindi)
    (
        "🌟 <b>Into regional cinema?</b> We've got you covered!\n\n"
        "Join <b>MovYra</b> for the best of:\n\n"
        "🎬 Malayalam cinema 🌴\n"
        "🎬 Tamil cinema 🌟\n"
        "🎬 Hindi blockbusters 🎭\n"
        "🎬 Telugu & Kannada updates\n\n"
        "First reviews, cast news & box-office updates!\n\n"
        f"👉 <a href='{config.MAIN_GROUP_LINK}'>Join MovYra</a>\n\n"
        "🌐 movyra.com"
    ),

    # 5 — General Entertainment
    (
        "🎉 <b>Your one-stop entertainment destination!</b>\n\n"
        "Join <b>MovYra Community</b> today 🎬\n\n"
        "🍿 Movie recommendations daily\n"
        "🍿 Celebrity news & updates\n"
        "🍿 Award season coverage\n"
        "🍿 Watch-along events\n\n"
        f"👉 <a href='{config.MAIN_GROUP_LINK}'>Join MovYra</a>\n\n"
        "🌐 movyra.com"
    ),
]


def get_invite_template(index: int = 0) -> str:
    """Return one of the 5 invite templates. Wraps around if index > 4."""
    return INVITE_TEMPLATES[index % len(INVITE_TEMPLATES)]


# ─── DAILY SCHEDULED CONTENT ──────────────────────────────────────────────────

def daily_recommendation(movie_name: str, reason: str, link: str) -> str:
    return (
        "🌅 <b>Good Morning, Movie Lovers!</b>\n\n"
        f"🎬 <b>Today's Pick:</b> {movie_name}\n\n"
        f"💡 {reason}\n\n"
        f"🔗 <a href='{link}'>Read Full Review on MovYra</a>\n\n"
        "#MovYra #MovieOfTheDay"
    )


def trending_update(movies: list) -> str:
    """movies = list of (rank, title, rating) tuples."""
    lines = "\n".join(
        f"{rank}. <b>{title}</b> — ⭐ {rating}/10"
        for rank, title, rating in movies
    )
    return (
        "📈 <b>Trending on MovYra Right Now</b>\n\n"
        f"{lines}\n\n"
        f"🌐 <a href='{config.WEBSITE_BASE_URL}/trending'>See All Trending</a>\n\n"
        "#MovYra #Trending"
    )


def ott_release_alert(releases: list) -> str:
    """releases = list of (platform, title, date) tuples."""
    lines = "\n".join(
        f"📺 <b>{title}</b> — {platform} | {date}"
        for platform, title, date in releases
    )
    return (
        "🎬 <b>OTT Releases This Week</b>\n\n"
        f"{lines}\n\n"
        f"🌐 <a href='{config.WEBSITE_BASE_URL}/ott'>Full OTT Calendar</a>\n\n"
        "#OTT #MovYra #Streaming"
    )


def movie_trivia(question: str, options: list) -> str:
    """Build a trivia poll caption."""
    opt_text = "\n".join(f"  {chr(65+i)}) {o}" for i, o in enumerate(options))
    return (
        "🧠 <b>Movie Trivia Time!</b>\n\n"
        f"❓ {question}\n\n"
        f"{opt_text}\n\n"
        "Reply with your answer! 👇\n\n"
        "#Trivia #MovYra"
    )


# ─── WELCOME / SYSTEM MESSAGES ────────────────────────────────────────────────

WELCOME_ADMIN = (
    "👋 <b>Welcome to MovYra Bot Admin Panel!</b>\n\n"
    "Here's what you can do:\n\n"
    "📣 <b>Promotions</b>\n"
    "  /addpromo — Add new movie promotion\n"
    "  /listpromos — View all promotions\n"
    "  /editpromo [id] — Edit a promotion\n"
    "  /deletepromo [id] — Delete a promotion\n\n"
    "👥 <b>Groups</b>\n"
    "  /addgroup [id] [name] — Add a group\n"
    "  /removegroup [id] — Remove a group\n"
    "  /listgroups — List all groups\n\n"
    "⚙️ <b>Scheduler</b>\n"
    "  /pause — Pause auto-posting\n"
    "  /resume — Resume auto-posting\n"
    "  /setinterval [minutes] — Change interval\n"
    "  /broadcast — Send promo to all groups NOW\n\n"
    "📨 <b>Invites</b>\n"
    "  /setinvite [1-5] — Set invite template\n"
    "  /sendinvite [group_id] — Send invite to group\n\n"
    "📊 <b>Info</b>\n"
    "  /status — Bot status\n"
    "  /help — This help message"
)

WELCOME_MEMBER = (
    "👋 <b>Welcome to MovYra Community!</b> 🎬\n\n"
    "We're your #1 destination for movie reviews, OTT updates, and more.\n\n"
    "📌 Rules:\n"
    "  • Be respectful to all members\n"
    "  • No spam or self-promotion\n"
    "  • Movie topics only\n"
    "  • Use topics/categories to post\n\n"
    f"🌐 Website: <a href='{config.WEBSITE_BASE_URL}'>movyra.com</a>"
)

PAUSED_MSG    = "⏸️ Auto-posting has been <b>paused</b>."
RESUMED_MSG   = "▶️ Auto-posting has been <b>resumed</b>."
NOT_ADMIN_MSG = "🚫 This command is only available to MovYra admins."
