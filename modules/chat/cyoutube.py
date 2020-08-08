# Copyright (C) 2016   CzT/Vladislav Ivanov
import time

import datetime
import logging.config
import os
import webbrowser

import threading

from youtube import API
from modules.gui import MODULE_KEY
from modules.helper.message import TextMessage, SystemMessage
from modules.helper.module import ChatModule, Channel, CHANNEL_ONLINE, CHANNEL_OFFLINE, CHANNEL_PENDING, \
    CHANNEL_DISABLED

from modules.helper.system import translate_key, get_wx_parent, get_secret
from modules.interface.types import LCStaticBox, LCPanel, LCText, LCBool, LCButton, LCLabel

logging.getLogger('irc').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('youtube')

CLIENT_ID = get_secret('youtube.clientid')
CLIENT_SECRET = get_secret('youtube.clientsecret')

FILE_ICON = os.path.join('img', 'youtube.png')

ICON = 'https://www.youtube.com/favicon.ico'
YT_SCOPE = 'https://www.googleapis.com/auth/youtube.readonly'

LOCAL_API_URL = 'http://localhost:{}/rest/cyoutube/oauth'
LOCAL_API_URL_RESP = 'http://localhost:{}/rest/cyoutube/oauth_response'

MAX_RESULTS = 50


def register_oauth(event):
    parent = get_wx_parent(event.GetEventObject()).Parent

    port = parent.loaded_modules['webchat'].port
    api = parent.loaded_modules['cyoutube'].api
    auth_url = api.get_auth_url(redirect_uri=LOCAL_API_URL.format(port), scope=[YT_SCOPE])
    webbrowser.open(auth_url)
    pass


CONF_DICT = LCPanel(icon=FILE_ICON)
CONF_DICT['config'] = LCStaticBox()
CONF_DICT['config']['register_oauth'] = LCButton(register_oauth)
CONF_DICT['config']['warning'] = LCLabel(translate_key('cyoutube.warning'))
CONF_DICT['api'] = LCStaticBox(hidden=True)
CONF_DICT['api']['access_token'] = LCText('')
CONF_DICT['api']['refresh_token'] = LCText('')
CONF_DICT['api']['expires_in'] = LCText('')
CONF_DICT['api']['date_acquired'] = LCText('')


CONF_GUI = {
    'config': {
        'hidden': ['host', 'port'],
    },
    'hidden': ['api'],
    'non_dynamic': [],
    'ignored_sections': ['config.register_oauth']
}

CONNECTION_SUCCESS = translate_key(MODULE_KEY.join(['youtube', 'connection_success']))
CONNECTION_DIED = translate_key(MODULE_KEY.join(['youtube', 'connection_died']))
CONNECTION_CLOSED = translate_key(MODULE_KEY.join(['youtube', 'connection_closed']))
CONNECTION_JOINING = translate_key(MODULE_KEY.join(['youtube', 'joining']))
CHANNEL_JOIN_SUCCESS = translate_key(MODULE_KEY.join(['youtube', 'join_success']))
CHANNEL_JOINING = translate_key(MODULE_KEY.join(['youtube', 'joining']))


class NotLiveError(Exception):
    pass


class YTMessage(TextMessage):
    def __init__(self, message, **kwargs):
        text = message['snippet']['displayMessage']

        super().__init__(text=text, platform_id='yt', icon=ICON, **kwargs)


class YTSystemMessage(SystemMessage):
    def __init__(self, text, category='system', **kwargs):
        super().__init__(text, category, platform_id='yt', icon=ICON, user='YouTube', **kwargs)


class YTReader(threading.Thread):
    def __init__(self, api, live_id, channel, queue, channel_module):
        self.api = api
        self.live_id = live_id
        self.token = None
        self.channel = channel
        self.queue = queue
        self.c_module = channel_module

        super().__init__(daemon=True)

    def run(self):
        while True:
            snippet = self.api.get('liveChat/messages', liveChatId=self.live_id, part='snippet', pageToken=self.token)
            self.process_message(snippet['items'])
            self.token = snippet['nextPageToken']

            v_req = self.api.get('videos', id=self.channel, part='liveStreamingDetails')
            self.c_module.viewers = v_req['items'][0]['liveStreamingDetails']['concurrentViewers']

            sleep_time = snippet['pollingIntervalMillis']/1000.00
            log.debug(f'sleeping for {sleep_time}s')
            time.sleep(sleep_time)

    def process_message(self, messages):
        users_to_get = [message['snippet']['authorChannelId'] for message in messages]
        users = {}

        for val in range(0, len(users_to_get), MAX_RESULTS):
            users_req = self.api.get('channels', id=','.join(users_to_get[val:val+MAX_RESULTS]), maxResults=MAX_RESULTS)
            users.update({user['id']: user['snippet']['title'] for user in users_req['items']})

        for message in messages:
            user = users.get(message['snippet']['authorChannelId'])
            if not user:
                log.info('asd')
            chat_msg = YTMessage(message, user=user, mid=message['id'])
            self.queue.put(chat_msg)


class YTChannel(threading.Thread, Channel):
    def __init__(self, cqueue, chat, chat_module):
        self.chat_module = chat_module
        self.reader = None
        self.live_id = None

        threading.Thread.__init__(self, daemon=True)
        Channel.__init__(self, chat, cqueue)

    def run(self):
        try_count = 0
        # We are connecting via IRC handler.
        while True:
            try_count += 1
            try:
                if self._status == CHANNEL_DISABLED:
                    break

                log.info("Connecting, try %s", try_count)
                self._status = CHANNEL_PENDING
                if self.load_config():
                    self.reader = YTReader(self.chat_module.api, self.live_id, self.channel, self.queue, self)

                    self._status = CHANNEL_ONLINE
                    self.reader.run()
                    log.info("Connection closed")
                self._status = CHANNEL_OFFLINE
                break
            except NotLiveError as exc:
                log.error('Channel is not live, please check the URL')
                self._status = CHANNEL_OFFLINE
                break
            except Exception as exc:
                log.exception(exc)
            time.sleep(5)

    def load_config(self):
        try:
            video = self.chat_module.api.get('videos', id=self.channel, part='liveStreamingDetails')
            details = video['items'][0]['liveStreamingDetails']
            if 'activeLiveChatId' in details:
                self.live_id = details['activeLiveChatId']
            else:
                raise NotLiveError()
        except NotLiveError as exc:
            raise exc
        except Exception as exc:
            log.exception(f'Unable to find proper details for the videoid. Error: {exc}')

        return True

    def stop(self):
        try:
            self._status = CHANNEL_DISABLED
            del self.reader
        except Exception as exc:
            pass


# Overlap with youtube-python module, have to have different name than Youtube
class CYoutube(ChatModule):
    def __init__(self, *args, **kwargs):
        super().__init__(config=CONF_DICT, gui=CONF_GUI, *args, **kwargs)
        log.info("Initializing twitch chat")

        self.api = None
        self.api_functioning = False

        self.rest_add('GET', 'oauth', self.parse_oauth_request)

    def load_module(self, *args, **kwargs):
        self.api = API(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, api_key='')
        warning = self.config['config']['warning']
        if self.get_config('api', 'refresh_token').value:
            expires = int(self.get_config('api', 'expires_in').value)
            date = datetime.datetime.fromisoformat(self.get_config('api', 'date_acquired').value)
            delta = datetime.timedelta(seconds=expires)
            if date + delta < datetime.datetime.now():
                ret_data = self.api.refresh_token(self.get_config('api', 'refresh_token').value)
                ret_data.update({'refresh_token': self.get_config('api', 'refresh_token').value})
                self.update_tokens(ret_data)
            self.api = API(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, api_key='',
                           access_token=self.config['api']['access_token'].value)
            self.api_functioning = True
            warning.hidden = True
        else:
            warning.color = 'red'
            warning.hidden = False
        super().load_module(*args, **kwargs)

    def _add_channel(self, chat):
        if self.api_functioning:
            self.channels[chat] = YTChannel(self.queue, chat, chat_module=self)
            self.channels[chat].start()

    def update_tokens(self, data):
        self.config['api']['access_token'].value = data['access_token']
        self.config['api']['refresh_token'].value = data['refresh_token']
        self.config['api']['expires_in'].value = str(data['expires_in'])
        self.config['api']['date_acquired'].value = datetime.datetime.now().isoformat()
        self.apply_settings()

    def apply_settings(self, **kwargs):
        if 'system_exit' in kwargs:
            super().apply_settings(**kwargs)
            return
        token = self.get_config('api', 'refresh_token')
        if token.value:
            self.api_functioning = True
            label = self.get_config('config', 'warning')
            label.color = None
            label.update()
            label.hide(True)

        super().apply_settings(**kwargs)

    def parse_oauth_request(self, *args, **kwargs):
        code = kwargs.get('code')
        port = self._loaded_modules['webchat'].port
        ret_data = self.api.exchange_code(code=code, redirect_uri=LOCAL_API_URL.format(port))

        self.update_tokens(ret_data)
        return 'Token Requested successfully'

    def api_call(self, key):
        pass
