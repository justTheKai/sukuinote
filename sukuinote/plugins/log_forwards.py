import html
import asyncio
from pyrogram import Client, filters
from .. import config, slave, log_errors, app_user_ids

logged = set()
lock = asyncio.Lock()

@Client.on_message(filters.incoming & filters.forwarded & (filters.group | filters.channel))
@log_errors
async def log_forwards(client, message):
    if not config['config'].get('log_forwards'):
        return
    if not message.from_user or message.from_user.id in app_user_ids:
        return
    for i in app_user_ids:
        if message.forward_from:
            if i == message.forward_from.id:
                forwardee = app_user_ids[i]
                break
        j = app_user_ids[i].first_name
        if app_user_ids[i].last_name:
            j += f' {app_user_ids[i].last_name}'
        if j == message.forward_sender_name:
            forwardee = app_user_ids[i]
            break
    else:
        return
    identifier = (message.chat.id, message.message_id)
    async with lock:
        if identifier in logged:
            return
        chat_text = html.escape(message.chat.title)
        if message.chat.username:
            chat_text = f'<a href="https://t.me/{message.chat.username}">{chat_text}</a>'
        text = f'<b>Forwarded Event</b>\n- <b>Chat:</b> {chat_text} '
        if message.chat.is_verified:
            chat_text += '<code>[VERIFIED]</code> '
        if message.chat.is_support:
            chat_text += '<code>[SUPPORT]</code> '
        if message.chat.is_scam:
            chat_text += '<code>[SCAM]</code> '
        text += f'[<code>{message.chat.id}</code>]\n- <b>Forwarder:</b> '
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
        text += f'- <b><a href="{message.link}">Message'
        mtext = (message.text or message.caption or '').strip()
        if mtext:
            text += ':'
        text += '</a></b>'
        if mtext:
            text += f' {html.escape(mtext.strip()[:2000])}'
        text += '\n- <b>Forwardee:</b> '
        user_text = forwardee.first_name
        if forwardee.last_name:
            user_text += f' {forwardee.last_name}'
        user_text = '<code>[DELETED]</code>' if forwardee.is_deleted else html.escape(user_text or 'Empty???')
        if forwardee.is_verified:
            user_text += ' <code>[VERIFIED]</code>'
        if forwardee.is_support:
            user_text += ' <code>[SUPPORT]</code>'
        if forwardee.is_scam:
            user_text += ' <code>[SCAM]</code>'
        text += f'{user_text} [<code>{forwardee.id}</code>]'
        while True:
            try:
                await slave.send_message(config['config']['log_chat'], text, disable_web_page_preview=True)
            except FloodWait as ex:
                await asyncio.sleep(ex.x + 1)
            else:
                break
        logged.add(identifier)
