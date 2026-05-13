import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from database import db
from scheduler import scheduler
from groups import group_manager
from promotions import promotion_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
ADMIN_IDS = [int(x.strip()) for x in os.environ.get('ADMIN_USER_IDS', '').split(',') if x.strip()]

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def start(update, context):
    if is_admin(update.effective_user.id):
        stats = db.get_statistics()
        await update.message.reply_text(f"🎬 MovYra Bot Active!\n\nPromotions: {stats['promo_count']}\nGroups: {stats['group_count']}\nSent: {stats['total_sent']}")
    else:
        await update.message.reply_text("🎬 Welcome to MovYra Bot!")

async def status(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only")
        return
    stats = db.get_statistics()
    await update.message.reply_text(f"Status: {'Running' if stats['auto_posting'] else 'Paused'}\nInterval: {stats['interval']} min\nPromotions: {stats['promo_count']}\nGroups: {stats['group_count']}")

async def pause(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only")
        return
    scheduler.pause()
    await update.message.reply_text("Paused")

async def resume(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only")
        return
    scheduler.resume()
    await update.message.reply_text("Resumed")

async def setinterval(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only")
        return
    if context.args:
        try:
            minutes = int(context.args[0])
            scheduler.update_interval(minutes)
            await update.message.reply_text(f"Interval set to {minutes} minutes")
        except:
            await update.message.reply_text("Invalid number")
    else:
        await update.message.reply_text("Usage: /setinterval 30")

async def listpromos(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only")
        return
    promos = db.get_all_promotions()
    if not promos:
        await update.message.reply_text("No promotions")
        return
    msg = "Promotions:\n"
    for p in promos:
        msg += f"ID {p['id']}: {p['title']} - {'Active' if p['active'] else 'Inactive'}\n"
    await update.message.reply_text(msg)

async def addgroup(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only")
        return
    if len(context.args) >= 2:
        group_id = context.args[0]
        group_name = ' '.join(context.args[1:])
        db.add_group(group_id, group_name)
        await update.message.reply_text(f"Group {group_name} added")
    else:
        await update.message.reply_text("Usage: /addgroup -100xxxxx GroupName")

async def listgroups(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only")
        return
    groups = db.get_all_groups()
    if not groups:
        await update.message.reply_text("No groups")
        return
    msg = "Groups:\n"
    for g in groups:
        msg += f"{g['group_name']} - {g['group_id']}\n"
    await update.message.reply_text(msg)

async def broadcast(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only")
        return
    promo = db.get_next_promotion()
    if not promo:
        await update.message.reply_text("No active promotions")
        return
    groups = db.get_all_groups()
    await update.message.reply_text(f"Broadcasting to {len(groups)} groups...")
    for group in groups:
        await scheduler.post_to_group(promo, group)
        await asyncio.sleep(1)
    await update.message.reply_text("Broadcast complete")

async def help_command(update, context):
    help_text = """
Commands:
/start - Welcome
/status - Bot status
/listpromos - List promotions
/listgroups - List groups
/setinterval N - Set interval
/pause - Pause auto
/resume - Resume auto
/broadcast - Send now
/addgroup ID Name - Add group
"""
    await update.message.reply_text(help_text)

def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not set!")
        return
    
    global application
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("pause", pause))
    application.add_handler(CommandHandler("resume", resume))
    application.add_handler(CommandHandler("setinterval", setinterval))
    application.add_handler(CommandHandler("listpromos", listpromos))
    application.add_handler(CommandHandler("listgroups", listgroups))
    application.add_handler(CommandHandler("addgroup", addgroup))
    application.add_handler(CommandHandler("broadcast", broadcast))
    
    scheduler.start()
    
    logger.info("Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
