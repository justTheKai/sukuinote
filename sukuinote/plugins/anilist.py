import html
from pyrogram import Client, filters
from pyrogram.types.messages_and_media import Photo
from pyrogram.errors.exceptions.forbidden_403 import Forbidden
from .. import slave, config, help_dict, log_errors, public_log_errors

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['anilist', 'al', 'alc', 'alchar', 'alcharacter', 'anilistc', 'anilistchar', 'anilistcharacter'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def anilist(client, message):
    bot = await slave.get_me()
    query = message.command
    page = 1
    character = 'c' in query.pop(0)
    if query and query[0].isnumeric():
        page = int(query.pop(0))
    page -= 1
    if page < 0:
        page = 0
    elif page > 9:
        page = 9
    query = ' '.join(query)
    if not query:
        return
    results = await client.get_inline_bot_results(bot.username or bot.id, f'al{"c" if character else ""} ' + query)
    if not results.results:
        await message.reply_text('No results')
        return
    try:
        await message.reply_inline_bot_result(results.query_id, results.results[page].id)
    except IndexError:
        await message.reply_text(f'There are only {len(results.results)} results')
    except Forbidden:
        text = {'message': results.results[page].send_message.message, 'entities': results.results[page].send_message.entities}
        try:
            photo = Photo._parse(client, results.results[page].photo)
            await message.reply_cached_media(photo.file_id, photo.file_ref, caption=text, parse_mode='through')
        except Forbidden:
            await message.reply_text(text, disable_web_page_preview=True, parse_mode='through')

help_dict['anilist'] = ('Anilist',
'''{prefix}anilist <i>&lt;query&gt;</i> - Searches for anime/manga named <i>&lt;query&gt;</i> on Anilist
Aliases: {prefix}al
Can also be activated inline with: @{bot} anilist <i>&lt;query&gt;</i> or @{bot} al <i>&lt;query&gt;</i>

{prefix}anilistc <i>&lt;query&gt;</i> - Searches for characters named <i>&lt;query&gt;</i> on Anilist
Aliases: {prefix}alc, alchar, alcharacter, anilistchar, anilistcharacter
Can also be activated inline with: @{bot} anilistc <i>&lt;query&gt;</i> or @{bot} alc <i>&lt;query&gt;</i>''')
