import html
import tempfile
from pyrogram import Client, filters
from .. import config, help_dict, log_errors, session, progress_callback, public_log_errors

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.outgoing & filters.command('cat', prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def cat(client, message):
    media = message.document
    if not media and not getattr(message.reply_to_message, 'empty', True):
        media = message.reply_to_message.document
    if not media:
        await message.reply_text('Document required')
        return
    done = False
    with tempfile.NamedTemporaryFile() as file:
        reply = await message.reply_text('Downloading...')
        await client.download_media(media, file_name=file.name, progress=progress_callback, progress_args=(reply, 'Downloading...', False))
        with open(file.name) as nfile:
            while True:
                chunk = nfile.read(4096)
                if not chunk:
                    break
                chunk = f'<code>{html.escape(chunk)}</code>'
                if done:
                    await message.reply_text(chunk, quote=False)
                else:
                    await reply.edit_text(chunk)
                    done = True

help_dict['cat'] = ('cat', '{prefix}cat <i>(as caption of text file or reply)</i> - Outputs file\'s text to Telegram')
