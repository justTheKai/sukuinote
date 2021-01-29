import os
import html
import tempfile
from pyrogram import Client, filters
from .. import config, help_dict, log_errors, session, progress_callback, public_log_errors

@Client.on_message(~filters.forwarded & ~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command('cat', prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def cat(client, message):
    media = (message.text or message.caption).markdown.split(' ', 1)[1:]
    if media:
        media = os.path.expanduser(media[0])
    else:
        media = message.document
        if not media and not getattr(message.reply_to_message, 'empty', True):
            media = message.reply_to_message.document
        if not media:
            await message.reply_text('Document or local file path required')
            return
    done = False
    reply = rfile = None
    try:
        if not isinstance(media, str):
            rfile = tempfile.NamedTemporaryFile()
            reply = await message.reply_text('Downloading...')
            await client.download_media(media, file_name=rfile.name, progress=progress_callback, progress_args=(reply, 'Downloading...', False))
            media = rfile.name
        with open(media, 'rb') as file:
            while True:
                chunk = file.read(4096)
                if not chunk:
                    break
                if not chunk.strip():
                    continue
                chunk = f'<code>{html.escape(chunk.decode())}</code>'
                if done:
                    await message.reply_text(chunk, quote=False)
                else:
                    await getattr(reply, 'edit_text', message.reply_text)(chunk)
                    done = True
    finally:
        if rfile:
            rfile.close()

help_dict['cat'] = ('cat', '''{prefix}cat <i>(as caption of text file or reply)</i> - Outputs file's text to Telegram
{prefix}cat <i>&lt;path to local file&gt;</i> - Outputs file's text to Telegram''')
