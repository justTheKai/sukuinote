import os
import signal
from pyrogram import Client, filters
from .. import config, help_dict, log_errors, public_log_errors

@Client.on_message(~filters.forwarded & ~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['poweroff', 'shutdown', 'stop'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def poweroff(client, message):
    await message.reply_text('Goodbye')
    os.kill(os.getpid(), signal.SIGINT)

help_dict['poweroff'] = ('Poweroff',
'''{prefix}poweroff - Turns off the userbot
Aliases: {prefix}shutdown, {prefix}stop''')
