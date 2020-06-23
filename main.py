#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
import time
import urllib.parse
from functools import wraps
from pathlib import Path
from uuid import uuid4

import telegram
from logzero import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler)
from tinydb import TinyDB, Query
from decouple import config

data_dir = Path('~', 'messagemerger').expanduser()
data_dir.mkdir(parents=True, exist_ok=True)
db = TinyDB(data_dir / 'db.json')
user_db = Query()

LIST_OF_ADMINS = [691609650, 62056065]


def start(update, context):
    text = "I am a bot to help you merge messages.\n"
    text += "Forward a bunch of messages and send /done command when you're done."
    update.message.reply_text(text)


def send_help(update, context):
    update.message.reply_text("Use /start to get information on how to use me.")


def get_admin_ids(context, chat_id):
    return [admin.user.id for admin in context.bot.get_chat_administrators(chat_id)]


def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            print("Unauthorized access denied for {}.".format(user_id))
            return
        return func(update, context, *args, **kwargs)

    return wrapped


def store_forwarded_message(update, context):
    user_id = update.message.from_user.id
    try:
        first_name = update.message.forward_from.first_name + ': '
    except AttributeError:
        first_name = "HiddenUser: "
    text = first_name + update.message.text_markdown
    scheme = [text]
    context.user_data.setdefault(user_id, []).extend(scheme)


def split_messages(update, context):
    user_id = update.message.from_user.id
    try:
        current_contents = context.user_data[user_id]
        text = "\n".join(current_contents)
        first_name = text.split(': ')[0]
        text = text.replace(str(first_name) + ': ', '')
        text = re.sub(r'\n+', '\n', text).strip()
        messages = text.splitlines()
        filtered_chars = ['$', '&', '+', ',', ':', ';', '=', '?', '@', '#', '|', '<', '>', '.', '^', '*', '(', ')', '%',
                          '!', '-', '_']
        for part in messages:
            if part in filtered_chars:
                continue
            else:
                update.message.reply_text(part, parse_mode=ParseMode.MARKDOWN)
    except IndexError:
        pass
    except KeyError:
        update.message.reply_text("Forward a merged message.")
    finally:
        context.user_data.clear()


def done(update, context):
    user_id = update.message.from_user.id
    try:
        data = context.user_data[user_id]
        message_id = uuid4()
        db.insert({'message_id': str(message_id), 'text': data})
        text = "\n".join([i.split(': ', 1)[1] for i in data])
        if len(text) <= 4096:
            url_msg = text.replace('_', '__').replace('*', '**')
            query = urllib.parse.quote(url_msg)
            share_url = 'tg://msg_url?url=' + query
            markup = InlineKeyboardMarkup([[InlineKeyboardButton("📬 Share", url=share_url)], [
                InlineKeyboardButton("📢 Publish to channel", callback_data='{}'.format(message_id)),
                InlineKeyboardButton("🗣 Show names", callback_data='{};show_dialogs'.format(message_id))]])
            update.message.reply_text(text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        else:
            messages = [text[i: i + 4096] for i in range(0, len(text), 4096)]
            for part in messages:
                update.message.reply_text(part, parse_mode=ParseMode.MARKDOWN)
                time.sleep(1)
    except KeyError:
        update.message.reply_text("Forward some messages.")
    finally:
        context.user_data.clear()


def post(update, context):
    user_id = update.effective_user.id
    context.bot.send_chat_action(chat_id=user_id, action=telegram.ChatAction.TYPING)
    query = update.callback_query
    query_data = query.data.split(';')
    message_id = query_data[0]
    search = db.get(user_db['message_id'] == message_id)
    json_str = json.dumps(search)
    resp = json.loads(json_str)
    data = resp.get('text')
    try:
        if query_data[1] == "show_dialogs":
            text = "\n".join(data)
            url_msg = text.replace('_', '__').replace('*', '**')
            share_url = 'tg://msg_url?url=' + urllib.parse.quote(url_msg)
            markup = InlineKeyboardMarkup([[InlineKeyboardButton("📬 Share", url=share_url)], [
                InlineKeyboardButton("📢 Publish to channel", callback_data='{}'.format(message_id)),
                InlineKeyboardButton("🙈 Hide names", callback_data='{};hide_dialogs'.format(message_id))]])
            query.edit_message_text(text=text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        elif query_data[1] == "hide_dialogs":
            text = "\n".join([i.split(': ', 1)[1] for i in data])
            url_msg = text.replace('_', '__').replace('*', '**')
            share_url = 'tg://msg_url?url=' + urllib.parse.quote(url_msg)
            markup = InlineKeyboardMarkup([[InlineKeyboardButton("📬 Share", url=share_url)], [
                InlineKeyboardButton("📢 Publish to channel", callback_data='{}'.format(message_id)),
                InlineKeyboardButton("🗣 Show names", callback_data='{};show_dialogs'.format(message_id))]])
            query.edit_message_text(text=text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        else:
            search = db.search(user_db['user_id'] == str(user_id))
            json_str = json.dumps(search[0])
            resp = json.loads(json_str)
            channel_id = resp['channel_id']
            text = "\n".join([i.split(': ', 1)[1] for i in data])
            context.bot.send_message(chat_id=channel_id, text=text, parse_mode=ParseMode.MARKDOWN)
            context.bot.answer_callback_query(query.id, text="The message has been posted on your channel.",
                                              show_alert=False)
    except TypeError:
        context.bot.send_message(chat_id=user_id,
                                 text="I am unable to retrieve and process this message, please forward this "
                                      "again.")
    except IndexError:
        context.bot.send_message(chat_id=user_id, text="You haven't added any channel yet, send /add followed by your "
                                                       "channel's id which can be found using @ChannelIdBot.")


def add(update, context):
    user_id = update.message.from_user.id
    channel_id = ' '.join(context.args)
    if context.bot.id in get_admin_ids(context.bot, channel_id):
        db.insert({'user_id': str(user_id), 'channel_id': str(channel_id)})
        context.bot.send_message(chat_id=channel_id, text="Your channel has been successfully added!")
        context.bot.send_message(chat_id=user_id, text="Your channel has been successfully added!")
    else:
        context.bot.send_message(chat_id=user_id,
                                 text="Please double-check if the bot is an administrator in your channel.")


@restricted
def backup(update, context):
    update.message.reply_document(document=open('db.json', 'rb'))


@restricted
def backup_handler(update, context):
    file = context.bot.get_file(update.message.document.file_id)
    file_name = update.message.document.file_name
    os.remove(file_name)
    file.download(file_name)
    update.message.reply_text(text="Alright! I have uploaded the backup.")


def error_callback(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    updater = Updater(config("BOT_TOKEN"), use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", send_help))
    dp.add_handler(CommandHandler("add", add))
    dp.add_handler((CallbackQueryHandler(post)))
    dp.add_handler(CommandHandler("done", done))
    dp.add_handler(CommandHandler("split", split_messages))
    dp.add_handler(MessageHandler(Filters.forwarded & Filters.text, store_forwarded_message))
    dp.add_handler(CommandHandler("backup", backup))
    dp.add_handler(MessageHandler(Filters.document, backup_handler))
    dp.add_error_handler(error_callback)
    updater.start_polling()
    logger.info("Ready to rock..!")
    updater.idle()


if __name__ == "__main__":
    main()
