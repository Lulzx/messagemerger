#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import time
import urllib.parse
from uuid import uuid4

import telegram
from logzero import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, \
    ParseMode
from telegram.ext import (Updater, CommandHandler, InlineQueryHandler, MessageHandler, Filters, CallbackQueryHandler)
from tinydb import TinyDB, Query

db = TinyDB('db.json')
user = Query()


def start(update, context):
    text = "I am a bot to help you merge messages.\n"
    text += "Forward a bunch of messages and send /done command when you're done."
    update.message.reply_text(text)


def get_admin_ids(context, chat_id):
    return [admin.user.id for admin in context.bot.get_chat_administrators(chat_id)]


def store_forwarded_message(update, context):
    user_id = update.message.chat_id
    try:
        first_name = update.message.forward_from.first_name + ': '
    except AttributeError:
        first_name = "HiddenUser: "
    text = first_name + update.message.text_markdown
    scheme = [text]
    try:
        context.user_data[user_id].extend(scheme)
    except KeyError:
        context.user_data[user_id] = []
        context.user_data[user_id].extend(scheme)


def split(update, context):
    user_id = update.message.chat_id
    try:
        text = ""
        data = context.user_data[user_id]
        for i in data:
            text += i + "\n"
        text = text.replace('{}: '.format(text.split(': ')[0]), '')
        text = text.replace('\n\n', '\n').replace('\n\n', '\n').replace(u"\u2800", '')
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
    context.user_data.clear()


def inline(update, context, switch_pm=None):
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


def done(update, context):
    user_id = update.message.chat_id
    try:
        text = ""
        data = context.user_data[user_id]
        message_id = uuid4()
        db.insert({'message_id': f'{message_id}', 'text': data})
        if len(data) <= 4096:
            for i in data:
                i = i.split(': ', 1)[1]
                text += i + "\n"
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
    context.user_data.clear()


def post(update, context):
    user_id = update.effective_user.id
    context.bot.send_chat_action(chat_id=user_id, action=telegram.ChatAction.TYPING)
    query = update.callback_query
    query_data = query.data.split(';')
    message_id = query_data[0]
    search = db.get(user['message_id'] == message_id)
    json_str = json.dumps(search)
    resp = json.loads(json_str)
    text = ""
    data = resp['text']
    for i in data:
        i = i.split(': ', 1)[1]
        text += i + "\n"
    try:
        if query_data[1] == "show_dialogs":
            text = ""
            for i in data:
                text += i + "\n"
            url_msg = text.replace('_', '__').replace('*', '**')
            share_url = 'tg://msg_url?url=' + urllib.parse.quote(url_msg)
            markup = InlineKeyboardMarkup([[InlineKeyboardButton("📬 Share", url=share_url)], [
                InlineKeyboardButton("📢 Publish to channel", callback_data='{}'.format(message_id)),
                InlineKeyboardButton("🙈 Hide names", callback_data='{};hide_dialogs'.format(message_id))]])
            query.edit_message_text(text=text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        elif query_data[1] == "hide_dialogs":
            url_msg = text.replace('_', '__').replace('*', '**')
            share_url = 'tg://msg_url?url=' + urllib.parse.quote(url_msg)
            markup = InlineKeyboardMarkup([[InlineKeyboardButton("📬 Share", url=share_url)], [
                InlineKeyboardButton("📢 Publish to channel", callback_data='{}'.format(message_id)),
                InlineKeyboardButton("🗣 Show names", callback_data='{};show_dialogs'.format(message_id))]])
            query.edit_message_text(text=text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
        else:
            search = db.search(user['user_id'] == f'{user_id}')
            json_str = json.dumps(search[0])
            resp = json.loads(json_str)
            channel_id = resp['channel_id']
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
    user_id = update.message.chat_id
    channel_id = ' '.join(context.args)
    if context.bot.id in get_admin_ids(context.bot, channel_id):
        db.insert({'user_id': f'{user_id}', 'channel_id': f'{channel_id}'})
        context.bot.send_message(chat_id=channel_id, text="Your channel has been successfully added!")
        context.bot.send_message(chat_id=user_id, text="Your channel has been successfully added!")
    else:
        context.bot.send_message(chat_id=user_id,
                                 text="Please double-check if the bot is an administrator in your channel.")


def backup(update, context):
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    if username == 'Lulzx':
        context.bot.send_document(chat_id=chat_id, document=open('db.json', 'rb'))
    else:
        context.bot.send_message(chat_id=chat_id, text="Only for admins for maintenance purpose.")


def backup_handler(update, context):
    file = context.bot.getFile(update.message.document.file_id)
    file_name = update.message.document.file_name
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    if username == 'Lulzx':
        os.remove(file_name)
        file.download(file_name)
        context.bot.send_message(chat_id=chat_id, text="Alright! I have uploaded the backup.")


def error_callback(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    try:
        token = sys.argv[1]
    except IndexError:
        token = os.environ.get("TOKEN")
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(InlineQueryHandler(inline))
    dp.add_handler(CommandHandler("add", add))
    dp.add_handler((CallbackQueryHandler(post)))
    dp.add_handler(CommandHandler("done", done))
    dp.add_handler(CommandHandler("split", split))
    dp.add_handler(MessageHandler(Filters.forwarded & Filters.text, store_forwarded_message))
    dp.add_handler(CommandHandler("backup", backup))
    dp.add_handler(MessageHandler(Filters.document, backup_handler))
    dp.add_error_handler(error_callback)
    updater.start_polling()
    logger.info("Ready to rock..!")
    updater.idle()


if __name__ == "__main__":
    main()
