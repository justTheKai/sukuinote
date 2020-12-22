import html
import asyncio
from pyrogram import Client, filters
from pyrogram.errors.exceptions.flood_420 import FloodWait
from .. import config, slave, log_errors

reported = set()
lock = asyncio.Lock()

@Client.on_message(~filters.chat(config['config']['log_chat']) & filters.regex(r'(?:^|\s+)@admins?(?:$|\W+)|^[/!](?:report|admins?)(?:$|\W+)') & filters.group)
@log_errors
async def log_reports(client, message):
    if not config['config']['log_reports']:
        return
    identifier = (message.chat.id, message.message_id)
    async with lock:
        if identifier in reported:
            return
        chat_text = html.escape(message.chat.title)
        if message.chat.username:
            chat_text = f'<a href="https://t.me/{message.chat.username}">{chat_text}</a>'
        text = f'<b>Report Event</b>\n- <b>Chat:</b> {chat_text} '
        if message.chat.is_verified:
            chat_text += '<code>[VERIFIED]</code> '
        if message.chat.is_support:
            chat_text += '<code>[SUPPORT]</code> '
        if message.chat.is_scam:
            chat_text += '<code>[SCAM]</code> '
        text += f'[<code>{message.chat.id}</code>]\n- <b>Reporter:</b> '
        user_text = message.from_user.first_name
        if message.from_user.last_name:
            user_text += f' {message.from_user.last_name}'
        user_text = '<code>[DELETED]</code>' if message.from_user.is_deleted else html.escape(user_text or 'Empty???')
        if message.from_user.is_verified:
            user_text += ' <code>[VERIFIED]</code>'
        if message.from_user.is_support:
            user_text += ' <code>[SUPPORT]</code>'
        if message.from_user.is_scam:
            user_text += ' <code>[SCAM]</code>'
        text += f'{user_text} [<code>{message.from_user.id}</code>]\n'
        start, end = message.matches[0].span()
        text += f'- <b><a href="{message.link}">Report Message'
        mtext = (message.text or message.caption or '').strip()
        if start or end < len(mtext):
            text += ':'
        text += '</a></b>'
        if start or end < len(mtext):
            text += f' {html.escape(mtext.strip()[:1000])}'
        reply = message.reply_to_message
        if not getattr(reply, 'empty', True):
            text += '\n- <b>Reportee:</b> '
            if reply.from_user:
                user_text = reply.from_user.first_name
                if reply.from_user.last_name:
                    user_text += f' {reply.from_user.last_name}'
                user_text = '<code>[DELETED]</code>' if reply.from_user.is_deleted else html.escape(user_text or 'Empty???')
                if reply.from_user.is_verified:
                    user_text += ' <code>[VERIFIED]</code>'
                if reply.from_user.is_support:
                    user_text += ' <code>[SUPPORT]</code>'
                if reply.from_user.is_scam:
                    user_text += ' <code>[SCAM]</code>'
                user_text += f' [<code>{reply.from_user.id}</code>]'
            else:
                user_text = 'None???'
            text += f'{user_text}\n- <b><a href="{reply.link}">Reported Message'
            mtext = reply.text or reply.caption or ''
            if mtext.strip():
                text += ':'
            text += f'</a></b> {html.escape(mtext.strip()[:1000])}'
        while True:
            try:
                reply = await slave.send_message(config['config']['log_chat'], text, disable_web_page_preview=True)
            except FloodWait as ex:
                await asyncio.sleep(ex.x + 1)
            else:
                break
        reported.add(identifier)
        reported.add((reply.chat.id, reply.message_id))
