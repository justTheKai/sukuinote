import time
from pyrogram import Client, filters
from .. import config, help_dict, log_errors, public_log_errors

@Client.on_message(~filters.forwarded & ~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['ping', 'pong'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def ping_pong(client, message):
    strings = {
        'ping': 'Pong!',
        'pong': 'Ping!'
    }
    text = strings[message.command[0].lower()]
    start = time.time()
    reply = await message.reply_text(text)
    end = time.time()
    await reply.edit_text(f'{text}\n<i>{round((end-start)*1000)}ms</i>')

help_dict['ping'] = ('Ping',
'''{prefix}ping - Pong!
{prefix}pong - Ping!''')
