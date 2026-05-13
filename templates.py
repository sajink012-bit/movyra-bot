WELCOME_MESSAGE = """
🎬 **Welcome to MovYra Bot!**

Your movie promotion and community management bot.

Use /help to see all commands
"""

HELP_MESSAGE = """
🤖 **MovYra Bot Commands**

/addpromo - Add new promotion
/listpromos - Show all promotions
/setinterval [min] - Change frequency
/pause - Pause auto-posting
/resume - Resume auto-posting
/status - Show bot status
/broadcast - Send instant promotion
/addgroup [id] [name] - Add group
/listgroups - Show all groups
"""

STATUS_TEMPLATE = """
📊 **Bot Status**

**Status:** {status}
**Interval:** {interval} minutes
**Promotions:** {promo_count}
**Groups:** {group_count}
**Messages Sent:** {total_sent}
"""
