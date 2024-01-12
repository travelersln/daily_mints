# reminder_tasks.py
import discord
from discord.ext import tasks
from discord.ui import Button, View
from datetime import datetime, timedelta
import re
from database_operations import add_reminder, get_pending_reminders, update_reminder_status, delete_past_reminders, check_reminder_exists
import logging

# Configura el logging
logger = logging.getLogger('reminder_tasks')

def extract_event_time(event_text):
    match = re.search(r'<t:(\d+):F>', event_text)
    if match:
        event_unix_time = int(match.group(1))
        return datetime.utcfromtimestamp(event_unix_time)
    return None

class ReminderButton(Button):
    def __init__(self, label, custom_id, event_text):
        super().__init__(style=discord.ButtonStyle.primary, label=label, emoji="🔔", custom_id=custom_id)
        self.event_text = event_text

    async def callback(self, interaction):
        event_time = extract_event_time(self.event_text)
        if event_time:
            exists = check_reminder_exists(interaction.user.id, self.custom_id)
            if exists:
                await interaction.response.send_message("You have already set a reminder for this event.", ephemeral=True)
            else:
                guild_id = interaction.guild.id
                channel_id = interaction.channel.id
                message_id = interaction.message.id
                add_reminder(interaction.user.id, self.custom_id, event_time, guild_id, channel_id, message_id)
                await interaction.response.send_message(f"Reminder set for {event_time - timedelta(minutes=30)}.", ephemeral=True)

class ReminderView(View):
    def __init__(self, event_texts):
        super().__init__()
        for i, event_text in enumerate(event_texts):
            custom_id = f"reminder_{i+1}"
            self.add_item(ReminderButton(f"Mint {i+1}", custom_id, event_text))


@tasks.loop(seconds=60)
async def reminder_check(bot):
    logger.info("Checking reminders...")
    try:
        reminders = get_pending_reminders()
        current_time = datetime.utcnow()
        logger.debug(f"Current time: {current_time}")
        for reminder in reminders:
            time_difference = (reminder.event_time - current_time).total_seconds()
            logger.debug(f"Checking reminder for user {reminder.user_id}: event time {reminder.event_time}, time difference {time_difference}")
            if 0 < time_difference <= 1800 and reminder.status == 'pending':
                logger.info(f"Preparing to send a reminder for user {reminder.user_id}")
                try:
                    user = await bot.fetch_user(reminder.user_id)
                    message_link = f"https://discord.com/channels/{reminder.guild_id}/{reminder.channel_id}/{reminder.message_id}"
                    message_content = f"¡Remember the mint {reminder.custom_id} from your reminder at {message_link}!"
                    message = await user.send(message_content)
                    if message:
                        logger.info(f"Sent a reminder to user {reminder.user_id}. Now updating status.")
                        update_reminder_status(reminder.id, 'notified')
                        logger.info(f"Updated reminder status to 'notified' for user {reminder.user_id}")
                    else:
                        logger.error(f"Failed to send reminder: No message object returned for user {reminder.user_id}")
                except Exception as e:
                    logger.error(f"Failed to send reminder to user {reminder.user_id}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An error occurred in reminder_check: {e}", exc_info=True)
@tasks.loop(minutes=1)
async def cleanup_past_reminders():
    logger.info("Cleaning up past reminders...")
    try:
        current_time = datetime.utcnow()
        delete_past_reminders(current_time) 
        logger.info("Past reminders have been cleaned up.")
    except Exception as e:
        logger.error(f"An error occurred in cleanup_past_reminders: {e}", exc_info=True)

def setup_tasks(bot):
    reminder_check.start(bot)
    cleanup_past_reminders.start()
