#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import sys
import time
from uuid import uuid4

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (Updater, CommandHandler, InlineQueryHandler, MessageHandler, Filters, CallbackQueryHandler)
from tinydb import TinyDB, Query

try:
    db = TinyDB('db.json')
except PermissionError:
    db = TinyDB('C:/Users/Lulzx/My Documents/msg/db.json')
user = Query()

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def start(bot, update):
    update.message.reply_text("I am a bot to help you merge messages.\n"
                              "Forward a bunch of messages and send /done command when you're done.")


def get_admin_ids(bot, chat_id):
    return [admin.user.id for admin in bot.get_chat_administrators(chat_id)]


def forward(bot, update, chat_data):
    user_id = update.message.from_user.id
    try:
        messages = str(chat_data[user_id])

    except KeyError:
        messages = ""
    chat_data[user_id] = "{}\n".format(messages + update.message.text)


def inline(bot, update, switch_pm=None):
    query = update.inline_query.query
    text = ""
    if not switch_pm:
        switch_pm = ['Switch to PM', 'help']
    try:
        search = db.get(user['message_id'] == query)
        json_str = json.dumps(search)
        resp = json.loads(json_str)
        try:
            text = resp['text']
        except TypeError:
            if search is None:
                text = "Go to private"
        result = [
            InlineQueryResultArticle(
                id=uuid4(),
                title="Your message",
                description="Click here to send in this chat",
                input_message_content=InputTextMessageContent(
                    "{}".format(text)))]
        update.inline_query.answer(result, switch_pm_text=f'{switch_pm[0]}', switch_pm_parameter=f'{switch_pm[1]}')
    except IndexError:
        pass


def done(bot, update, chat_data):
    user_id = update.message.from_user.id
    try:
        text = str(chat_data[user_id])
        message_id = uuid4()
        db.insert({'message_id': f'{message_id}', 'text': f'{text}'})
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("📬 Share", switch_inline_query=f'{message_id}')], [
            InlineKeyboardButton("📢 Publish to channel", callback_data='{}'.format(message_id))]])
        if len(text) <= 4096:
            update.message.reply_text(text, reply_markup=markup)
        else:
            messages = [text[i: i + 4096] for i in range(0, len(text), 4096)]
            for part in messages:
                update.message.reply_text(part)
                time.sleep(1)
    except KeyError:
        update.message.reply_text("Forward some messages.")
    chat_data.clear()


def post(bot, update):
    user_id = update.effective_user.id
    bot.send_chat_action(chat_id=user_id, action=telegram.ChatAction.TYPING)
    query = update.callback_query
    search = db.get(user['message_id'] == query.data)
    json_str = json.dumps(search)
    resp = json.loads(json_str)
    text = resp['text']
    search = db.search(user['user_id'] == f'{user_id}')
    try:
        json_str = json.dumps(search[0])
        resp = json.loads(json_str)
        channel_id = resp['channel_id']
        bot.send_message(chat_id=channel_id, text=text)
        bot.answer_callback_query(query.id, text="The message has been posted on your channel.", show_alert=False)
    except IndexError:
        bot.send_message(chat_id=user_id, text="You haven't added any channel yet, send /add followed by your "
                                               "channel's id.")


def add(bot, update, args):
    user_id = update.message.from_user.id
    channel_id = ' '.join(args)
    if bot.id in get_admin_ids(bot, channel_id):
        db.upsert({'user_id': f'{user_id}', 'channel_id': f'{channel_id}'}, user.user_id == user_id)
        bot.send_message(chat_id=channel_id, text="Your channel has been successfully added!")
        bot.send_message(chat_id=user_id, text="Your channel has been successfully added!")
    else:
        bot.send_message(chat_id=user_id, text="Please double-check if the bot is an administrator in your channel.")


def backup(bot, update):
    username = update.message.from_user.username
    chat_id = update.message.from_user.id
    if username == 'Lulzx':
        try:
            bot.send_document(chat_id=chat_id, document=open('db.json', 'rb'))
        except FileNotFoundError:
            bot.send_document(chat_id=chat_id, document=open('C:/Users/Lulzx/My Documents/msg/db.json', 'rb'))
    else:
        bot.send_message(chat_id=chat_id, text="Only for admins for maintenance purpose.")


def backup_handler(bot, update):
    file = bot.getFile(update.message.document.file_id)
    file_name = update.message.document.file_name
    username = update.message.from_user.username
    chat_id = update.message.from_user.id
    if username == 'Lulzx':
        os.remove(file_name)
        file.download(file_name)
        bot.send_message(chat_id=chat_id, text="Alright! I have uploaded the backup.")
    else:
        bot.send_message(chat_id=chat_id, text="Only for admins for maintenance purpose.")


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def main():
    try:
        token = sys.argv[1]
    except IndexError:
        token = os.environ.get("TOKEN")
    updater = Updater(token)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(InlineQueryHandler(inline))
    dp.add_handler(CommandHandler("add", add, pass_args=True))
    dp.add_handler((CallbackQueryHandler(post)))
    dp.add_handler(CommandHandler("done", done, pass_chat_data=True))
    dp.add_handler(MessageHandler(Filters.forwarded & Filters.text, forward, pass_chat_data=True))
    dp.add_handler(CommandHandler("backup", backup))
    dp.add_handler(MessageHandler(Filters.document, backup_handler))
    dp.add_error_handler(error)
    updater.start_polling()
    logger.info("Ready to rock..!")
    updater.idle()


if __name__ == "__main__":
    main()
