#!/usr/bin/env python

"""
Simple Bot to sending media files to Telegram channel according to a interval
schedule.
This Bot uses the Updater class to handle the bot and the JobQueue to send
messages in linear defined time intervals.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import html
import json
import logging
import traceback
from pathlib import Path

from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler

# The token you got from @botfather when you created the bot
API_TOKEN = '{{YOU_API_TOKEN}}'

# This can be your own ID, or one for a developer group/channel.
# You can use the /uinfo command of this bot to see your chat id.
DEVELOPER_CHAT_ID = 12345678

# Users who can execute commands with elevated rights.
PRIVILEGED_USERS = (DEVELOPER_CHAT_ID,)

# The channel to which the bot will publish content.
# Bot must be an administrator of channel & have permission to post.
CHANNEL = '@you_channel_to_post'

# The destination path for the source media to be published.
RESOURCE_PATH = Path('./data')

# The destination path for media already published.
PUBLISHED_ARCHIVE = Path('./data/published_archive')

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


def start_handler(update: Update, _):
    """Initial user communication dialog."""
    info_text = '*tg_schedule_woodpecker* _v1.0.1_\n' \
                'Hello! I am sending media files to Telegram channel ' \
                'according to selected interval schedule.\n\n' \
                'You can control me by sending these commands:\n\n' \
                '*Commands*\n' \
                '/start - Initial point (now you here)\n' \
                '/help - List of available commands (same as /start)\n' \
                '/send - Post next media to channel now\n' \
                '/set [[interval]] - Create schedule job for publishing a ' \
                'limited set of media\n' \
                '/clear - Clear the current job queue\n' \
                '/uinfo - You personal Telegram account information'

    update.message.reply_text(info_text, parse_mode=ParseMode.MARKDOWN)


def error_handler(update, context):
    """Log the error and send a telegram message to notify the developer."""
    error = context.error
    tb_list = traceback.format_exception(None, error, error.__traceback__)
    tb_string = ''.join(tb_list)

    logger.error(msg="Exception was raised:", exc_info=error)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    update_str = json.dumps(update_str, indent=2, ensure_ascii=False)
    update_str = html.escape(update_str)
    chat_data = html.escape(str(context.chat_data))
    user_data = html.escape(str(context.user_data))

    message = (
        f'An exception was raised while handling an update\n'
        f'<pre>update = {update_str}</pre>\n\n'
        f'<pre>context.chat_data = {chat_data}</pre>\n\n'
        f'<pre>context.user_data = {user_data}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    context.bot.send_message(chat_id=DEVELOPER_CHAT_ID,
                             text=message,
                             parse_mode=ParseMode.HTML)


def check_access_rights(func):
    def wrapper(update, context):
        chat_id = update.message.chat_id

        if chat_id in PRIVILEGED_USERS:
            func(update, context)
        else:
            update.message.reply_text('Not enough access rights!')

    return wrapper


def uinfo_handler(update, _):
    """Handle /uinfo cmd. Provide personal Telegram account information."""
    user = update.message.from_user

    update.message.reply_text(
        f'Your Telegram personal info:\n'
        f'ID: *{user.id}*\n'
        f'Is BOT: *{user.is_bot}*\n\n'
        f'First name: *{user.first_name}*\n'
        f'Last name : *{user.last_name}*\n'
        f'Username : *{user.username}*\n\n'
        f'Language code: *{user.language_code}*\n\n'
        f'Can join groups : *{user.can_join_groups}*\n'
        f'Can read all group messages : *{user.can_read_all_group_messages}*\n'
        f'Supports inline queries : *{user.supports_inline_queries}*',
        parse_mode=ParseMode.MARKDOWN)


def send_typed_media(resource_path, bot, channel):
    """Send file as bytes by `resource_path`.
    Send type based on file extension."""
    ext = resource_path.suffix.lower()
    media_resource = open(resource_path, 'rb')

    if ext in ('.jpeg', '.jpg', '.png'):
        return bot.send_photo(chat_id=channel, photo=media_resource)
    elif ext in ('.mp4', '.mov', '.gif', '.webp'):
        return bot.send_animation(chat_id=channel, animation=media_resource)


def post_next_media(bot, channel, from_path, to_path):
    """Publish first available media file from iterable path object.
    After file will be moved to archive folder."""
    for item in from_path.iterdir():
        if item.is_dir():
            continue

        message = send_typed_media(item, bot, channel)

        if message and hasattr(message, 'date'):
            item.replace(to_path.joinpath(item.name))

            return message


def publish_next_media_to_channel(context, chat_id):
    """Publish next media to channel now."""
    message = post_next_media(context.bot, CHANNEL, RESOURCE_PATH,
                              PUBLISHED_ARCHIVE)

    if message is not None:
        message_id = message.message_id
        context.bot.send_message(chat_id, f'Published message: #{message_id}')
    else:
        signal_empty_storage(context.bot, chat_id)
        clear(context.bot, context, chat_id)


@check_access_rights
def send_handler(update, context):
    """Handle /send cmd. Publish next media to channel now"""
    publish_next_media_to_channel(context, update.message.chat_id)


def send_callback(context):
    """Callback wrapper for publishing next media"""
    publish_next_media_to_channel(context, chat_id=context.job.context)


@check_access_rights
def set_handler(update, context):
    """Handle /set cmd. Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        # args[0] contain the time for the timer in seconds
        interval = int(context.args[0])
        name = str(chat_id)

        if interval < 0:
            raise ValueError('Invalid argument')

        remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_repeating(send_callback, interval,
                                        context=chat_id, name=name)

        start_queue_text = f'Next publish will be after {interval} seconds.'
        update.message.reply_text(start_queue_text)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <seconds>')


@check_access_rights
def clear_handler(update, context):
    """Handle /clear cmd. Remove the current job queue."""
    chat_id = update.message.chat_id
    clear(context.bot, context, chat_id)


def clear(bot, context, chat_id):
    """Clear the job queue by chat_id identifier"""
    job_removed = remove_job_if_exists(str(chat_id), context)

    text = 'Timer successfully cancelled!' if job_removed else 'You have no active timer.'
    bot.send_message(chat_id=chat_id, text=text)


def remove_job_if_exists(name, context):
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)

    if not current_jobs:
        return False

    for job in current_jobs:
        job.schedule_removal()

    return True


def signal_empty_storage(bot, chat_id):
    """Inform the user that the resource folder does not contain a valid
    media file."""
    warn_text = f'Resource folder don`t contain available media resource.'
    bot.send_message(chat_id=chat_id, text=warn_text)


def main() -> None:
    """Run bot."""
    updater = Updater(API_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_handler))
    dispatcher.add_handler(CommandHandler("help", start_handler))
    dispatcher.add_handler(CommandHandler("send", send_handler))
    dispatcher.add_handler(CommandHandler("set", set_handler))
    dispatcher.add_handler(CommandHandler("clear", clear_handler))
    dispatcher.add_handler(CommandHandler("uinfo", uinfo_handler))

    dispatcher.add_error_handler(error_handler)

    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
