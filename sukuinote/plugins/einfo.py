import re
import html
import asyncio
import datetime
from pyrogram import Client, filters
from .. import config, help_dict, get_entity, session, log_errors, public_log_errors

conversation_hack = dict()

DEAI_BAN_CODES = {
    "00": "Gban",
    "01": "Joinspam",
    "02": "Spambot",
    "03": "Generic spam",
    "04": "Scam",
    "05": "Illegal",
    "06": "Pornography",
    "07": "Nonsense",
    "08": "Chain bans",
    "09": "Special",
    "10": "Preemptive",
    "11": "Copyright",
    "12": "Admin rights abuse",
    "13": "Toxicity",
    "14": "Flood",
    "15": "Detected but not classified",
    "16": "Advanced detection",
    "17": "Reported",
    "18": "AI association",
    "19": "Impersonation",
    "20": "Malware",
    "21": "Ban evasion",
    "22": "PM spam",
    "23": "Spam adding members",
    "24": "RESERVED",
    "25": "RESERVED",
    "26": "Raid initiation",
    "27": "Raid participation"
}
DEAI_MODULE_CODES = {
    "0": "Gban",
    "1": "Database parser",
    "2": "Realtime",
    "3": "Profiler",
    "4": "Scraper",
    "5": "Association analytics",
    "6": "Codename Autobahn",
    "7": "Codename Polizei",
    "8": "Codename Gestapo"
}

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['einfo', 'externalinfo', 'sw', 'spamwatch', 'deai', 'spb', 'spamprotection', 'cas', 'combot', 'rose'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def fedstat(client, message):
    entity = message.from_user
    args = message.command
    command = args.pop(0).lower()
    if args:
        entity = ' '.join(args)
    elif not getattr(message.reply_to_message, 'empty', True):
        entity = message.reply_to_message.from_user or entity
    if isinstance(entity, str) and (not entity.isnumeric() and not entity.startswith('TEL-')):
        entity, entity_client = await get_entity(client, entity)
    if not isinstance(entity, str):
        entity = str(entity.id)
    if entity.startswith('TEL-') or int(entity) < 0 or command in ('spb', 'spamprotection'):
        await message.reply_text(f'Spam Protection:\n{await get_spam_protection(entity)}')
    elif command in ('sw', 'spamwatch'):
        await message.reply_text(f'SpamWatch:\n{await get_spamwatch(entity)}')
    elif command == 'deai':
        await message.reply_text(f'DEAI:\n{await get_deai(client, entity)}')
    elif command == 'rose':
        await message.reply_text(f'Rose Support:\n{await get_rose(client, entity)}')
    elif command in ('cas', 'combot'):
        await message.reply_text(f'CAS:\n{await get_cas(entity)}')
    else:
        spamwatch, deai, cas, spam_protection, rose = await asyncio.gather(get_spamwatch(entity), get_deai(client, entity), get_cas(entity), get_spam_protection(entity), get_rose(client, entity))
        await message.reply_text(f'''SpamWatch:
{spamwatch}

CAS:
{cas}

Rose Support:
{rose}

DEAI:
{deai}

Spam Protection:
{spam_protection}''')

async def get_spamwatch(entity):
    async with session.get(f'https://api.spamwat.ch/banlist/{entity}', headers={'Authorization': f'Bearer {config["config"]["spamwatch_api"]}'}) as resp:
        try:
            json = await resp.json()
        except BaseException as ex:
            return f'- <b>{resp.status}:</b> {html.escape(type(ex).__name__)}: {html.escape(str(ex))}'
    if 'code' in json:
        return f'- <b>{json["code"]}:</b> {html.escape(json.get("error", ""))}'
    return f'''- <b>Banned on:</b> {str(datetime.datetime.fromtimestamp(json["date"]))}
- <b>Reason:</b> {html.escape(json["reason"].strip())}'''

async def get_rose(client, entity):
    new_message = await client.send_message('missrose_bot', f'/fbanstat {entity} 86718661-6bfc-4bd0-9447-7c419eb08e69')
    identifier = (new_message.chat.id, new_message.message_id)
    conversation_hack[identifier] = None
    while not conversation_hack[identifier]:
        await asyncio.sleep(0.5)
    ntext = conversation_hack[identifier].split('\n')
    ntext.pop(0)
    if ntext:
        date = '-'.join(ntext.pop().split(' ')[-1].split('/')[::-1])
        reason = '\n'.join(ntext).strip()
        text = f'- <b>Banned on:</b> {date}'
        if reason:
            text += f'\n- <b>Reason:</b> {html.escape(reason)}'
        return text
    return '- <b>404:</b> Not Found'

async def get_deai(client, entity):
    new_message = await client.send_message('rsophiebot', f'/fcheck {entity} 845d33d3-0961-4e44-b4b5-4c57775fbdac')
    identifier = (new_message.chat.id, new_message.message_id)
    conversation_hack[identifier] = None
    while not conversation_hack[identifier]:
        await asyncio.sleep(0.5)
    ntext = conversation_hack[identifier].split('\n')
    ntext.pop(0)
    if ntext:
        ntext.pop(0)
    if ntext and not ntext[0].startswith('They aren\'t fbanned in the '):
        text = '- <b>Reason:</b> '
        ntext.pop(0)
        reason = '\n'.join(ntext).strip()
        text += html.escape(reason) or 'None'
        match = re.match(r'(?:AIdetection:)?((?:0x\d{2} )+)risk:(\S+) mod:X([0-8])(?: cmt:(.+))?', reason)
        if match:
            text += '\n- <b>Ban Codes:</b>\n'
            for i in match.group(1).split(' '):
                if i:
                    i = DEAI_BAN_CODES.get(i.strip()[2:], i.strip())
                    text += f'--- {i}\n'
            text += f'- <b>Risk Factor:</b> {match.group(2).capitalize()}\n'
            text += f'- <b>Module:</b> {DEAI_MODULE_CODES.get(match.group(3), match.group(3))}'
            comment = (match.group(4) or '').strip()
            if comment:
                text += f'\n- <b>Comment:</b> {html.escape(comment)}'
                match = re.match(r'^banstack trigger:0x(\d{2})$', comment)
                if match:
                    text += f'\n- <b>Banstack Trigger Code:</b> {DEAI_BAN_CODES.get(match.group(1), "0x" + match.group(1))}'
        return text
    return '- <b>404:</b> Not Found'

async def get_cas(entity):
    async with session.get(f'https://api.cas.chat/check?user_id={entity}') as resp:
        try:
            json = await resp.json()
        except BaseException as ex:
            return f'- <b>{resp.status}:</b> {html.escape(type(ex).__name__)}: {html.escape(str(ex))}'
    if json['ok']:
        return f'''- <b>Banned on:</b> {str(datetime.datetime.fromisoformat(json["result"]["time_added"][:-1]))}
- <b>Offenses:</b> {json["result"]["offenses"]}'''
    return f'- <b>XXX:</b> {html.escape(json.get("description", "XXX"))}'

async def get_spam_protection(entity):
    async with session.get(f'https://api.intellivoid.net/spamprotection/v1/lookup?query={entity}') as resp:
        try:
            json = await resp.json()
        except BaseException as ex:
            return f'- <b>{resp.status}:</b> {html.escape(type(ex).__name__)}: {html.escape(str(ex))}'
    if json['success']:
        text = ''
        if json['results']['private_telegram_id']:
            text += f'- <b>PTID:</b> <code>' + json['results']['private_telegram_id'] + "</code>\n"
        if json['results']['attributes']['intellivoid_accounts_verified']:
            text += '- <b>Intellivoid Account Linked:</b> Yes\n'
        if json['results']['attributes']['is_potential_spammer']:
            text += '- <b>Potential Spammer:</b> Yes\n'
        if json['results']['attributes']['is_operator']:
            text += '- <b>Operator:</b> Yes\n'
        if json['results']['attributes']['is_agent']:
            text += '- <b>Agent:</b> Yes\n'
        if json['results']['attributes']['is_whitelisted']:
            text += '- <b>Whitelisted:</b> Yes\n'
        text += f'- <b>Ham/Spam Prediction:</b> {json["results"]["spam_prediction"]["ham_prediction"] or 0}/{json["results"]["spam_prediction"]["spam_prediction"] or 0}'
        if json['results']['language_prediction']['language']:
            text += f'''\n- <b>Language Prediction:</b> {json["results"]["language_prediction"]["language"]}
- <b>Language Prediction Probability:</b> {json["results"]["language_prediction"]["probability"]}'''
        if json['results']['attributes']['is_blacklisted']:
            text += f'''\n- <b>Blacklist Flag:</b> {json["results"]["attributes"]["blacklist_flag"]}
- <b>Blacklist Reason:</b> {json["results"]["attributes"]["blacklist_reason"]}'''
        if json['results']['attributes']['original_private_id']:
            text += f'\n- <b>Original Private ID:</b> {json["results"]["attributes"]["original_private_id"]}'
        return text
    return f'- <b>{json["response_code"]}</b>: {json["error"]["error_code"]}: {json["error"]["type"]}: {html.escape(json["error"]["message"])}'

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.chat(['rsophiebot', 'missrose_bot']) & filters.incoming & filters.regex('^Federation ban info:\n|You ain\'t fbanned in this fed\.|^Failed to get user: unable to getChatMember: Bad Request: chat not found$|^.+ is not banned in this fed\.$|^.+ is currently banned in Rose Support Official, for the following reason:\n\n'))
async def fedstat_conversation_hack(client, message):
    reply = message.reply_to_message
    if not getattr(reply, 'empty', True):
        identifier = (reply.chat.id, reply.message_id)
        if identifier in conversation_hack:
            conversation_hack[identifier] = message.text
            await client.read_history(message.chat.id, message.message_id)

help_dict['einfo'] = ('External Info',
'''{prefix}externalinfo <i>&lt;user&gt;</i> - Get extended info of <i>&lt;user&gt;</i>
{prefix}externalinfo <i>(as reply to message)</i> - Get extended info of replied user
Aliases: {prefix}extinfo, {prefix}einfo

{prefix}spamwatch <i>&lt;user&gt;</i> - Get SpamWatch info of <i>&lt;user&gt;</i>
{prefix}spamwatch <i>(as reply to message)</i> - Get SpamWatch info of replied user
Aliases: {prefix}sw

{prefix}cas <i>&lt;user&gt;</i> - Get Combot Anti Spam info of <i>&lt;user&gt;</i>
{prefix}cas <i>(as reply to message)</i> - Get Combot Anti Spam info of replied user
Aliases: {prefix}combot

{prefix}rose <i>&lt;user&gt;</i> - Get Rose Support Federation info of <i>&lt;user&gt;</i>
{prefix}rose <i>(as reply to message)</i> - Get Rose Support Federation info of replied user

{prefix}deai <i>&lt;user&gt;</i> - Get DEAI info of <i>&lt;user&gt;</i>
{prefix}deai <i>(as reply to message)</i> - Get DEAI info of replied user

{prefix}spamprotection <i>&lt;user&gt;</i> - Get Spam Protection info of <i>&lt;user&gt;</i>
{prefix}spamprotection <i>(as reply to message)</i> - Get Spam Protection info of replied user
Aliases: {prefix}spb''')
