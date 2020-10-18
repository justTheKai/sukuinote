import re
import time
import json
import asyncio
import datetime
from pyrogram import Client, filters
from pyrogram.parser import html as pyrogram_html
from pyrogram.types import InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InlineQueryResultPhoto, InputMediaPhoto
from .. import session, app_user_ids, log_errors

all_anilists = dict()
anilists_lock = asyncio.Lock()

MEDIA_QUERY = '''query ($id: Int, $search: String) {
  Page (perPage: 10) {
    media (id: $id, search: $search) {
      id
      title {
        romaji
        english
        native
      }
      type
      format
      status
      description(asHtml: true)
      episodes
      duration
      chapters
      volumes
      genres
      synonyms
      averageScore
      nextAiringEpisode {
        airingAt
        timeUntilAiring
      }
      airingSchedule(notYetAired: true) {
        nodes {
          airingAt
          episode
        }
      }
      siteUrl
    }
  }
}'''
FORMAT_NAMES = {
    "TV": "TV",
    "TV_SHORT": "TV Short",
    "MOVIE": "Movie",
    "SPECIAL": "Special",
    "OVA": "OVA",
    "ONA": "ONA",
    "MUSIC": "Music",
    "MANGA": "Manga",
    "NOVEL": "Novel",
    "ONE_SHOT": "One Shot"
}
CHARACTER_QUERY = '''query ($id: Int, $search: String) {
  	Page (perPage: 10) {
	    characters (id: $id, search: $search) {
    	  name {
      	  full
        	native
        	alternative
      	}
      	description(asHtml: true)
      	image {
          large
        }
      	siteUrl
      }
    }
}'''

async def generate_media(anilist):
    title_romaji = anilist['title']['romaji']
    title_english = anilist['title']['english']
    title_native = anilist['title']['native']
    type = anilist['type'].capitalize()
    format = anilist['format']
    format = FORMAT_NAMES.get(format, format)
    status = anilist['status'].replace('_', ' ').title()
    description = (anilist.get('description') or '').strip()
    episodes = anilist['episodes']
    duration = anilist['duration']
    chapters = anilist['chapters']
    volumes = anilist['volumes']
    genres = ', '.join(anilist['genres'])
    synonyms = ', '.join(anilist['synonyms'])
    average_score = anilist['averageScore']
    site_url = anilist['siteUrl']
    text = f'<a href="{site_url}">{title_romaji}</a>'
    if title_english:
        text += f' ({title_english})'
    if title_native:
        text += f' ({title_native})'
    if synonyms:
        text += f'\n<b>Synonyms:</b> {synonyms}'
    if genres:
        text += f'\n<b>Genres:</b> {genres}'
    text += f'\n<b>Type:</b> {type}\n'
    if anilist['type'] != 'MANGA':
        text += f'<b>Format:</b> {format}\n'
    text += f'<b>Status:</b> {status}\n'
    if anilist['nextAiringEpisode']:
        airing_at = str(datetime.datetime.fromtimestamp(anilist['nextAiringEpisode']['airingAt']))
        time_until_airing = str(datetime.timedelta(seconds=anilist['nextAiringEpisode']['timeUntilAiring']))
        text += f'<b>Airing At:</b> {airing_at}\n<b>Airing In:</b> {time_until_airing}\n'
    if average_score is not None:
        text += f'<b>Average Score:</b> {average_score}%\n'
    if episodes:
        text += f'<b>Episodes:</b> '
        if anilist['airingSchedule'] and anilist['airingSchedule']['nodes']:
            text += f'{anilist["airingSchedule"]["nodes"][0]["episode"] - 1}/'
        text += f'{episodes}\n'
    if duration:
        text += f'<b>Duration:</b> {duration} minutes per episode\n'
    if chapters:
        text += f'<b>Chapters:</b> {chapters}\n'
    if volumes:
        text += f'<b>Volumes:</b> {volumes}\n'
    if description:
        text += '<b>Description:</b>\n'
        parser = pyrogram_html.HTML(None)
        total_length = len((await parser.parse(text))['message'])
        if len(description) > 1023-total_length:
            description = description[:1022-total_length] + '…'
        text += description
    return text, f"https://img.anili.st/media/{anilist['id']}"

async def generate_character(anilist):
    title_full = anilist['name']['full']
    title_native = anilist['name']['native']
    title_alternative = ', '.join(anilist['name']['alternative'])
    description = (anilist['description'] or '').strip()
    site_url = anilist['siteUrl']
    image = anilist['image']['large']
    text = f'<a href="{site_url}">{title_full}</a>'
    if title_native:
        text += f' ({title_native})'
    if title_alternative:
        text += f'\n<b>Synonyms:</b> {title_alternative}'
    if description:
        text += '\n'
        parser = pyrogram_html.HTML(None)
        total_length = len((await parser.parse(text))['message'])
        if len(description) > 1023-total_length:
            description = description[:1022-total_length] + '…'
        text += description
    return text, image

@Client.on_inline_query(filters.regex(r'^a(?:ni)?l(?:ist)?(c(?:har(?:acter)?)?)?\s+(.+)$'))
@log_errors
async def anilist_query(client, inline_query):
    if inline_query.from_user.id not in app_user_ids:
        await inline_query.answer([
            InlineQueryResultArticle('...no', InputTextMessageContent('...no'))
        ], cache_time=3600, is_personal=True)
        return
    character = bool(inline_query.matches[0].group(1))
    query = inline_query.matches[0].group(2).strip().lower()
    async with anilists_lock:
        if (character, query) not in all_anilists:
            async with session.post('https://graphql.anilist.co', data=json.dumps({'query': CHARACTER_QUERY if character else MEDIA_QUERY, 'variables': {'search': query}}), headers={'Content-Type': 'application/json', 'Accept': 'application/json'}) as resp:
                all_anilists[(character, query)] = (await resp.json())['data']['Page']['characters' if character else 'media']
    anilists = all_anilists[(character, query)]
    answers = []
    parser = pyrogram_html.HTML(client)
    for a, anilist in enumerate(anilists):
        text, image = await (generate_character if character else generate_media)(anilist)
        buttons = [InlineKeyboardButton('Back', 'anilist_back'), InlineKeyboardButton(f'{a + 1}/{len(anilists)}', 'anilist_nop'), InlineKeyboardButton('Next', 'anilist_next')]
        if not a:
            buttons.pop(0)
        if len(anilists) == a + 1:
            buttons.pop()
        split = text.split('\n', 1)
        title = (await parser.parse(split[0]))['message']
        try:
            description = (await parser.parse(split[1]))['message']
        except IndexError:
            description = None
        answers.append(InlineQueryResultPhoto(image, title=title, description=description, caption=text, reply_markup=InlineKeyboardMarkup([buttons]), id=f'anilist{a}-{time.time()}'))
    await inline_query.answer(answers, is_personal=True, is_gallery=False)

@Client.on_callback_query(filters.regex('^anilist_nop$'))
@log_errors
async def anilist_nop(client, callback_query):
    await callback_query.answer(cache_time=3600)

message_info = dict()
message_lock = asyncio.Lock()
@Client.on_chosen_inline_result()
@log_errors
async def anilist_chosen(client, inline_result):
    if inline_result.result_id.startswith('anilist'):
        match = re.match(r'^a(?:ni)?l(?:ist)?(c(?:har(?:acter)?)?)?\s+(.+)$', inline_result.query)
        if match:
            character = bool(match.group(1))
            query = match.group(2).strip().lower()
            if query:
                page = int(inline_result.result_id[7])
                message_info[inline_result.inline_message_id] = query, page, character
                async with anilists_lock:
                    if (character, query) not in all_anilists:
                        async with session.post('https://graphql.anilist.co', data=json.dumps({'query': CHARACTER_QUERY if character else MEDIA_QUERY, 'variables': {'search': query, 'page': 1, 'perPage': 10}}), headers={'Content-Type': 'application/json', 'Accept': 'application/json'}) as resp:
                            all_anilists[(character, query)] = (await resp.json())['data']['Page']['characters' if character else 'media']
                return
    inline_result.continue_propagation()

@Client.on_callback_query(filters.regex('^anilist_(back|next)$'))
@log_errors
async def anilist_move(client, callback_query):
    if callback_query.from_user.id not in app_user_ids:
        await callback_query.answer('...no', cache_time=3600, show_alert=True)
        return
    async with message_lock:
        if callback_query.inline_message_id not in message_info:
            await callback_query.answer('This message is too old', cache_time=3600, show_alert=True)
            return
        query, page, character = message_info[callback_query.inline_message_id]
        opage = page
        if callback_query.matches[0].group(1) == 'back':
            page -= 1
        elif callback_query.matches[0].group(1) == 'next':
            page += 1
        if page < 0:
            page = 0
        elif page > 9:
            page = 9
        if page != opage:
            async with anilists_lock:
                anilists = all_anilists[(character, query)]
            text, image = await (generate_character if character else generate_media)(anilists[page])
            buttons = [InlineKeyboardButton('Back', 'anilist_back'), InlineKeyboardButton(f'{page + 1}/{len(anilists)}', 'anilist_nop'), InlineKeyboardButton('Next', 'anilist_next')]
            if not page:
                buttons.pop(0)
            if len(anilists) == page + 1:
                buttons.pop()
            await callback_query.edit_message_media(InputMediaPhoto(image, caption=text), reply_markup=InlineKeyboardMarkup([buttons]))
            message_info[callback_query.inline_message_id] = query, page, character
    await callback_query.answer()
