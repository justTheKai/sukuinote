import html
from pyrogram import Client, filters
from .. import config, help_dict, log_errors, public_log_errors

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['d', 'del', 'delete'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def delete(client, message):
    messages = set((message.message_id,))
    reply = message.reply_to_message
    if not getattr(reply, 'empty', True):
        messages.add(reply.message_id)
    await client.delete_messages(message.chat.id, messages)

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['p', 'purge', 'sp', 'selfpurge'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def purge(client, message):
    selfpurge = 's' in message.command[0]
    ids = set((message.message_id,))
    reply = message.reply_to_message
    if not getattr(reply, 'empty', True):
        for i in await client.get_messages(message.chat.id, range(reply.message_id, message.message_id), replies=0):
            if selfpurge and not i.outgoing:
                continue
            ids.add(i.message_id)
    await client.delete_messages(message.chat.id, ids)

yeetpurge_info = {True: dict(), False: dict()}
@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['yp', 'yeetpurge', 'syp', 'selfyeetpurge'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def yeetpurge(client, message):
    reply = message.reply_to_message
    if getattr(message, 'empty', True):
        await message.delete()
        return
    info = yeetpurge_info['s' in message.command[0]]
    if message.chat.id not in info:
        resp = await message.reply_text('Reply to end destination')
        info[message.chat.id] = (message.message_id, resp.message_id, reply.message_id)
        return
    og_message, og_resp, og_reply = info.pop(message.chat.id)
    messages = set((og_message, og_resp, message.message_id))
    for i in await client.get_messages(message.chat.id, range(og_reply, reply.message_id + 1), replies=0):
        if 's' in message.command[0] and not i.outgoing:
            continue
        messages.add(i.message_id)
    await client.delete_messages(message.chat.id, messages)

help_dict['delete'] = ('Delete',
'''{prefix}delete <i>(as reply to a message)</i> - Deletes the replied to message
Aliases: {prefix}d, {prefix}del

{prefix}purge <i>(as reply to a message)</i> - Purges the messages between the one you replied (and including the one you replied)
Aliases: {prefix}p

{prefix}selfpurge <i>(as reply to a message)</i> - {prefix}p but only your messages
Aliases: {prefix}sp

{prefix}yeetpurge <i>(as reply to a message)</i> - Purges messages in between
Aliases: {prefix}yp

{prefix}selfyeetpurge <i>(as reply to a message)</i> - {prefix}yp but only your messages
Aliases: {prefix}syp''')
