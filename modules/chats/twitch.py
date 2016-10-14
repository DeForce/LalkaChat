import irc.client
import threading
import os
import re
import random
import requests
import logging
import logging.config
import Queue
from modules.helpers.parser import self_heal
from modules.helpers.modules import ChatModule
from modules.helpers.system import system_message

logging.getLogger('irc').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('twitch')
headers = {'Client-ID': '5jwove9dketiiz2kozapz8rhjdsxqxc'}
emote_bits_theme = 'dark'
emote_bits_type = 'static'
emote_bits_url = 'static-cdn.jtvnw.net/bits/{theme}/{type}/{color}/{size}'
NOT_FOUND = 'none'
SOURCE = 'tw'
SOURCE_ICON = 'https://www.twitch.tv/favicon.ico'
SYSTEM_USER = 'Twitch.TV'
CONF_DICT = [
            {'gui_information': {
                'category': 'chat'}},
            {'config__gui': {
                'for': 'config',
                'hidden': 'host, port'}},
            {'config': {
                'bttv': 'true',
                'channel': 'CHANGE_ME',
                'host': 'irc.twitch.tv',
                'port': '6667'}}
        ]


class TwitchMessageHandler(threading.Thread):
    def __init__(self, queue, twitch_queue, **kwargs):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.message_queue = queue
        self.twitch_queue = twitch_queue
        self.source = SOURCE

        self.nick = kwargs.get('nick')
        self.bttv = kwargs.get('bttv')
        self.badges = kwargs.get('badges')
        self.custom_badges = kwargs.get('custom_badges')

    def run(self):
        while True:
            self.process_message(self.twitch_queue.get())

    def process_message(self, msg):
        # After we receive the message we have to process the tags
        # There are multiple things that are available, but
        #  for now we use only display-name, which is case-able.
        # Also, there is slight problem with some users, they don't have
        #  the display-name tag, so we have to check their "real" username
        #  and capitalize it because twitch does so, so we do the same.
        comp = {'source': self.source,
                'source_icon': SOURCE_ICON,
                'badges': [],
                'emotes': [],
                'bttv_emotes': [],
                'user': 'TwitchSystem',
                'msg_type': msg.type}
        for tag in msg.tags:
            tag_value, tag_key = tag.values()
            if tag_key == 'display-name':
                if tag_value:
                    comp['user'] = tag_value
                else:
                    # If there is not display-name then we strip the user
                    #  from the string and use it as it is.
                    comp['user'] = msg.source.split('!')[0].capitalize()
            elif tag_key == 'badges' and tag_value:
                for badge in tag_value.split(','):
                    badge_tag, badge_size = badge.split('/')
                    # Fix some of the names
                    badge_tag = badge_tag.replace('moderator', 'mod')

                    if badge_tag in self.badges:
                        badge_info = self.badges.get(badge_tag)
                        if 'svg' in badge_info:
                            url = badge_info.get('svg')
                        elif 'image' in badge_info:
                            url = badge_info.get('image')
                        else:
                            url = 'none'
                    elif badge_tag in self.custom_badges:
                        badge_info = self.custom_badges.get(badge_tag)['versions'][badge_size]
                        url = badge_info.get('image_url_4x')
                    else:
                        url = NOT_FOUND
                    comp['badges'].append({'badge': badge_tag, 'size': badge_size, 'url': url})

            elif tag_key == 'emotes' and tag_value:
                emotes_split = tag_value.split('/')
                for emote in emotes_split:
                    emote_name, emote_pos_diap = emote.split(':')
                    emote_pos_list = emote_pos_diap.split(',')
                    comp['emotes'].append({'emote_id': emote_name, 'emote_pos': emote_pos_list})

        # Then we comp the message and send it to queue for message handling.
        comp['text'] = msg.arguments.pop()

        for word in comp['text'].split():
            if word in self.bttv:
                bttv_smile = self.bttv.get(word)
                comp['bttv_emotes'].append({'emote_id': bttv_smile['regex'],
                                            'emote_url': 'http:{0}'.format(bttv_smile['url'])})

        if re.match('^@?{0}( |,)'.format(self.nick), comp['text'].lower()):
            comp['pm'] = True

        self.message_queue.put(comp)


class IRC(irc.client.SimpleIRCClient):
    def __init__(self, queue, channel, **kwargs):
        irc.client.SimpleIRCClient.__init__(self)
        # Basic variables, twitch channel are IRC so #channel
        self.channel = "#" + channel.lower()
        self.nick = channel.lower()
        self.queue = queue
        self.twitch_queue = Queue.Queue()

        msg_handler = TwitchMessageHandler(queue, self.twitch_queue,
                                           nick=self.nick,
                                           bttv=kwargs.get('bttv_smiles_dict', {}),
                                           badges=kwargs.get('badges', {}),
                                           custom_badges=kwargs.get('custom_badges', {}))
        msg_handler.start()

    def on_connect(self, connection, event):
        log.info("Connected")

    def on_welcome(self, connection, event):
        log.info("Welcome Received, joining {0} channel".format(self.channel))
        system_message('Joining channel {0}'.format(self.channel), self.queue,
                       source=SOURCE, icon=SOURCE_ICON, from_user=SYSTEM_USER)
        # After we receive IRC Welcome we send request for join and
        #  request for Capabilites (Twitch color, Display Name,
        #  Subscriber, etc)
        connection.join(self.channel)
        connection.cap('REQ', ':twitch.tv/tags')

    def on_join(self, connection, event):
        log.info("Joined {0} channel".format(self.channel))
        system_message('Joined channel {0}'.format(self.channel), self.queue,
                       source=SOURCE, icon=SOURCE_ICON, from_user=SYSTEM_USER)

    def on_pubmsg(self, connection, event):
        self.twitch_queue.put(event)

    def on_action(self, connection, event):
        self.twitch_queue.put(event)


class twThread(threading.Thread):
    def __init__(self, queue, host, port, channel, bttv_smiles, anon=True):
        threading.Thread.__init__(self)
        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = True
        self.queue = queue

        self.host = host
        self.port = port
        self.channel = channel
        self.bttv_smiles = bttv_smiles
        self.kwargs = {}
        if bttv_smiles:
            self.kwargs['bttv_smiles_dict'] = {}

        # For anonymous log in Twitch wants username in special format:
        #
        #        justinfan(14d)
        #    ex: justinfan54826341875412
        #
        if anon:
            nick_length = 14
            self.nickname = "justinfan"

            for number in range(0, nick_length):
                self.nickname += str(random.randint(0, 9))

    def run(self):
        if self.load_config():
            # We are connecting via IRC handler.
            irc_client = IRC(self.queue, self.channel, **self.kwargs)
            irc_client.connect(self.host, self.port, self.nickname)
            irc_client.start()

    def load_config(self):
        try:
            request = requests.get("https://api.twitch.tv/kraken/channels/{0}".format(self.channel), headers=headers)
            if request.status_code == 200:
                log.info("Channel found, continuing")
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.error("Unable to get channel ID, error: {0}\nArgs: {1}".format(exc.message, exc.args))
            return False

        try:
            # Getting random IRC server to connect to
            request = requests.get("http://tmi.twitch.tv/servers?channel={0}".format(self.channel))
            if request.status_code == 200:
                self.host = random.choice(request.json()['servers']).split(':')[0]
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.error("Unable to get server list, error: {0}\nArgs: {1}".format(exc.message, exc.args))
            return False

        try:
            # Getting Better Twitch TV smiles
            if self.bttv_smiles:
                request = requests.get("https://api.betterttv.net/emotes")
                if request.status_code == 200:
                    for smile in request.json()['emotes']:
                        self.kwargs['bttv_smiles_dict'][smile.get('regex')] = smile
                else:
                    raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get BTTV smiles, error {0}\nArgs: {1}".format(exc.message, exc.args))

        try:
            # Getting standard twitch badges
            request = requests.get("https://api.twitch.tv/kraken/chat/{0}/badges".format(self.channel), headers=headers)
            if request.status_code == 200:
                self.kwargs['badges'] = request.json()
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get twitch badges, error {0}\nArgs: {1}".format(exc.message, exc.args))

        try:
            # Warning, undocumented, can change a LOT
            # Getting CUSTOM twitch badges
            request = requests.get("https://badges.twitch.tv/v1/badges/global/display")
            if request.status_code == 200:
                self.kwargs['custom_badges'] = request.json()['badge_sets']
            else:
                raise Exception("Not successful status code: {0}".format(request.status_code))
        except Exception as exc:
            log.warning("Unable to get twitch undocumented api badges, error {0}\n"
                        "Args: {1}".format(exc.message, exc.args))

        return True


class twitch(ChatModule):
    def __init__(self, queue, python_folder, **kwargs):
        ChatModule.__init__(self)
        log.info("Initializing twitch chat")

        # Reading config from main directory.
        conf_folder = os.path.join(python_folder, "conf")
        conf_file = os.path.join(conf_folder, "twitch.cfg")

        config = self_heal(conf_file, CONF_DICT)
        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config}

        config.read(conf_file)
        # Checking config file for needed variables
        config_tag = 'config'
        host = config.get(config_tag, 'host')
        port = int(config.get(config_tag, 'port'))
        channel = config.get(config_tag, 'channel')
        bttv_smiles = config.get(config_tag, 'bttv')

        # Creating new thread with queue in place for messaging tranfers
        tw = twThread(queue, host, port, channel, bttv_smiles)
        tw.start()
