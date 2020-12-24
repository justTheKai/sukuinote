import html
import asyncio
from pyrogram import Client, ContinuePropagation
from pyrogram.errors.exceptions.flood_420 import FloodWait
from pyrogram.raw.types import UpdateNewChannelMessage, UpdateNewMessage, MessageService, PeerChat, PeerChannel, MessageActionChatAddUser, MessageActionChatJoinedByLink
from .. import config, log_errors, slave

def sexy_user_name(user):
    text = user.first_name
    if user.last_name:
        text += ' ' + user.last_name
    return f'{"<code>[DELETED]</code>" if user.deleted else html.escape(text or "Empty???")} [<code>{user.id}</code>]'

handled = set()
lock = asyncio.Lock()
@Client.on_raw_update()
@log_errors
async def log_user_joins(client, update, users, chats):
    if isinstance(update, (UpdateNewChannelMessage, UpdateNewMessage)):
        message = update.message
        if isinstance(message, MessageService):
            action = message.action
            if isinstance(action, (MessageActionChatAddUser, MessageActionChatJoinedByLink)):
                if isinstance(message.peer_id, PeerChannel):
                    chat_id = message.peer_id.channel_id
                    sexy_chat_id = int('-100' + str(chat_id))
                elif isinstance(message.peer_id, PeerChat):
                    chat_id = message.peer_id.chat_id
                    sexy_chat_id = -chat_id
                else:
                    return
                peer = await client.resolve_peer(config['config']['log_chat'])
                if peer == message.peer_id:
                    return
                is_join = isinstance(action, MessageActionChatJoinedByLink)
                if not is_join:
                    is_join = action.users == [message.from_id.user_id]
                if is_join and not config['config']['log_user_joins']:
                    raise ContinuePropagation
                if not is_join and not config['config']['log_user_adds']:
                    raise ContinuePropagation
                text = f"<b>{'User Join Event' if is_join else 'User Add Event'}</b>\n- <b>Chat:</b> "
                atext = html.escape(chats[chat_id].title)
                if getattr(chats[chat_id], 'username', None):
                    atext = f'<a href="https://t.me/{chats[chat_id].username}">{atext}</a>'
                text += f"{atext} [<code>{sexy_chat_id}</code>]\n"
                async with lock:
                    if (sexy_chat_id, message.id) not in handled:
                        if is_join:
                            text += f'- <b>User:</b> {sexy_user_name(users[message.from_id])}\n'
                            if isinstance(action, MessageActionChatJoinedByLink):
                                text += f'- <b>Inviter:</b> {sexy_user_name(users[action.inviter_id])}'
                        else:
                            text += f'- <b>Adder:</b> {sexy_user_name(users[message.from_id])}\n- <b>Added Users:</b>\n'
                            for user in action.users:
                                text += f'--- {sexy_user_name(users[user])}\n'
                        while True:
                            try:
                                await slave.send_message(config['config']['log_chat'], text, disable_web_page_preview=True)
                            except FloodWait as ex:
                                await asyncio.sleep(ex.x + 1)
                            else:
                                break
                        handled.add((sexy_chat_id, message.id))
                        return
    raise ContinuePropagation
