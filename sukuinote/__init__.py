import os
import html
import time
import logging
import asyncio
import traceback
import functools
import yaml
import aiohttp
from datetime import timedelta
from pyrogram import Client, StopPropagation, ContinuePropagation
from pyrogram.types import Chat, User
from pyrogram.parser import parser
from pyrogram.errors.exceptions.bad_request_400 import PeerIdInvalid, ChannelInvalid

logging.basicConfig(level=logging.INFO)
with open('config.yaml') as config:
    config = yaml.safe_load(config)
loop = asyncio.get_event_loop()
help_dict = dict()

apps = []
app_user_ids = dict()
# this code here exists because i can't be fucked
class Parser(parser.Parser):
    async def parse(self, text, mode):
        if mode == 'through':
            return text
        return await super().parse(text, mode)
for session_name in config['config']['sessions']:
    app = Client(session_name, api_id=config['telegram']['api_id'], api_hash=config['telegram']['api_hash'], plugins={'root': os.path.join(__package__, 'plugins')}, parse_mode='html', workdir='sessions')
    app.parser = Parser(app)
    apps.append(app)
slave = Client('sukuinote-slave', api_id=config['telegram']['api_id'], api_hash=config['telegram']['api_hash'], plugins={'root': os.path.join(__package__, 'slave-plugins')}, parse_mode='html', bot_token=config['telegram']['slave_bot_token'], workdir='sessions')
slave.parser = Parser(slave)
session = aiohttp.ClientSession()

async def get_entity(client, entity):
    entity_client = client
    if not isinstance(entity, Chat):
        try:
            entity = int(entity)
        except ValueError:
            pass
        except TypeError:
            entity = entity.id
        try:
            entity = await client.get_chat(entity)
        except (PeerIdInvalid, ChannelInvalid):
            for app in apps:
                if app != client:
                    try:
                        entity = await app.get_chat(entity)
                    except (PeerIdInvalid, ChannelInvalid):
                        pass
                    else:
                        entity_client = app
                        break
            else:
                entity = await slave.get_chat(entity)
                entity_client = slave
    return entity, entity_client

async def get_user(client, entity):
    entity_client = client
    if not isinstance(entity, User):
        try:
            entity = int(entity)
        except ValueError:
            pass
        except TypeError:
            entity = entity.id
        try:
            entity = await client.get_users(entity)
        except PeerIdInvalid:
            for app in apps:
                if app != client:
                    try:
                        entity = await app.get_users(entity)
                    except PeerIdInvalid:
                        pass
                    else:
                        entity_client = app
                        break
            else:
                entity = await slave.get_users(entity)
                entity_client = slave
    return entity, entity_client

def log_errors(func):
    @functools.wraps(func)
    async def wrapper(client, *args):
        try:
            await func(client, *args)
        except (StopPropagation, ContinuePropagation):
            raise
        except Exception:
            tb = traceback.format_exc()
            try:
                await slave.send_message(config['config']['log_chat'], f'Exception occured in {func.__name__}\n\n{tb}', parse_mode=None)
            except Exception:
                logging.exception('Failed to log exception for %s as slave', func.__name__)
                tb = traceback.format_exc()
                for app in apps:
                    try:
                        await app.send_message(config['config']['log_chat'], f'Exception occured in {func.__name__}\n\n{tb}', parse_mode=None)
                    except Exception:
                        logging.exception('Failed to log exception for %s as app', func.__name__)
                        tb = traceback.format_exc()
                    else:
                        break
                raise
            raise
    return wrapper

def public_log_errors(func):
    @functools.wraps(func)
    async def wrapper(client, message):
        try:
            await func(client, message)
        except (StopPropagation, ContinuePropagation):
            raise
        except Exception:
            await message.reply_text(traceback.format_exc(), parse_mode=None)
            raise
    return wrapper

# https://stackoverflow.com/a/49361727
def format_bytes(size):
    size = int(size)
    # 2**10 = 1024
    power = 1000
    n = 0
    power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]+'B'}"

# https://stackoverflow.com/a/34325723
def return_progress_string(current, total):
    filled_length = int(30 * current // total)
    return '[' + '=' * filled_length + ' ' * (30 - filled_length) + ']'

# https://stackoverflow.com/a/852718
# https://stackoverflow.com/a/775095
def calculate_eta(current, total, start_time):
    if not current:
        return '00:00:00'
    end_time = time.time()
    elapsed_time = end_time - start_time
    seconds = (elapsed_time * (total / current)) - elapsed_time
    thing = ''.join(str(timedelta(seconds=seconds)).split('.')[:-1]).split(', ')
    thing[-1] = thing[-1].rjust(8, '0')
    return ', '.join(thing)

progress_callback_data = dict()
async def progress_callback(current, total, reply, text, upload):
    message_identifier = (reply.chat.id, reply.message_id)
    last_edit_time, prevtext, start_time = progress_callback_data.get(message_identifier, (0, None, time.time()))
    if current == total:
        try:
            progress_callback_data.pop(message_identifier)
        except KeyError:
            pass
    elif (time.time() - last_edit_time) > 1:
        handle = 'Upload' if upload else 'Download'
        if last_edit_time:
            speed = format_bytes((total - current) / (time.time() - start_time))
        else:
            speed = '0 B'
        text = f'''{text}
<code>{return_progress_string(current, total)}</code>

<b>Total Size:</b> {format_bytes(total)}
<b>{handle}ed Size:</b> {format_bytes(current)}
<b>{handle} Speed:</b> {speed}/s
<b>ETA:</b> {calculate_eta(current, total, start_time)}'''
        if prevtext != text:
            await reply.edit_text(text)
            prevtext = text
            last_edit_time = time.time()
            progress_callback_data[message_identifier] = last_edit_time, prevtext, start_time
