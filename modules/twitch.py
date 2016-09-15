import irc.client
import threading
import os
import re
import random
import requests
import logging
import logging.config
from modules.helpers.parser import FlagConfigParser

logging.getLogger('irc').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
log = logging.getLogger('twitch')


class IRC(irc.client.SimpleIRCClient):
    def __init__(self, queue, channel, badges, bttv):
        irc.client.SimpleIRCClient.__init__(self)
        # Basic variables, twitch channel are IRC so #channel
        self.channel = "#" + channel.lower()
        self.nick = channel.lower()
        self.source = "tw"
        self.queue = queue
        self.badges = badges
        self.bttv = bttv

    def on_connect(self, connection, event):
        log.info("Connected")

    def on_welcome(self, connection, event):
        log.info("Welcome Received")
        # After we receive IRC Welcome we send request for join and
        #  request for Capabilites (Twitch color, Display Name,
        #  Subscriber, etc)
        connection.join(self.channel)
        connection.cap('REQ', ':twitch.tv/tags')

    def on_join(self, connection, event):
        log.info("Joined {0} channel".format(self.channel))

    def on_pubmsg(self, connection, event):
        # After we receive the message we have to process the tags
        # There are multiple things that are available, but
        #  for now we use only display-name, which is case-able.
        # Also, there is slight problem with some users, they dont have
        #  the display-name tag, so we have to check their "real" username
        #  and capitalize it because twitch does so, so we do the same.
        comp = {'source': self.source}
        badges = []
        emotes = []
        for tag in event.tags:
            if tag['key'] == 'display-name':
                if tag['value'] is None:
                    # If there is not display-name then we strip the user
                    #  from the string and use it as it is.
                    comp['user'] = event.source.split('!')[0].capitalize()
                else:
                    comp['user'] = tag['value']
            if tag['key'] == 'badges':
                if tag['value'] is None:
                    pass
                else:
                    badges_pre = tag['value'].split(',')
                    for badge in badges_pre:
                        badge_pre = badge.split('/')
                        # Fix some of the names
                        badge_pre[0] = badge_pre[0].replace('moderator', 'mod')
                        if 'svg' in self.badges[badge_pre[0]]:
                            url = self.badges[badge_pre[0]]['svg']
                        else:
                            url = self.badges[badge_pre[0]]['image']
                        badges.append({'badge': badge_pre[0], 'size': badge_pre[1], 'url': url})

            if tag['key'] == 'emotes':
                if tag['value'] is None:
                    pass
                else:
                    emotes_pre = tag['value'].split('/')
                    for emote in emotes_pre:
                        emote_pre = emote.split(':')
                        emote_pos_pre = emote_pre[1].split(',')
                        emotes.append({'emote_id': emote_pre[0], 'emote_pos': emote_pos_pre})
        comp['badges'] = badges
        comp['emotes'] = emotes

        # Then we comp the message and send it to queue for message handling.
        comp['text'] = event.arguments[0]

        bt_emotes = []
        for bt_emote in self.bttv:
            if re.search('(^| )({0})( |$)'.format(re.escape(bt_emote['regex'])), comp['text']):
                bt_emotes.append({'emote_id': bt_emote['regex'], 'emote_url': 'http:{0}'.format(bt_emote['url'])})
        comp['bttv_emotes'] = bt_emotes

        if re.match('^@?{0}( |,)'.format(self.nick), comp['text'].lower()):
            comp['pm'] = True

        self.queue.put(comp)


class twThread(threading.Thread):
    def __init__(self, queue, host, port, channel, badges, bttv_smiles):
        threading.Thread.__init__(self)
        # Basic value setting.
        # Daemon is needed so when main programm exits
        # all threads will exit too.
        self.daemon = True
        self.queue = queue
        self.badges = badges

        self.host = host
        self.port = port
        self.channel = channel
        self.bttv_smiles = bttv_smiles

        # For anonymous log in Twitch wants username in special format:
        #
        #        justinfan(14d)
        #    ex: justinfan54826341875412
        #
        nick_length = 14
        self.nickname = "justinfan"

        for number in range(0, nick_length):
            self.nickname += str(random.randint(0, 9))

    def run(self):
        bttv_smiles = []
        if self.bttv_smiles:
            request = requests.get("https://api.betterttv.net/emotes")
            if request.status_code == 200:
                bttv_smiles = request.json()['emotes']

        # We are connecting via IRC handler.
        ircClient = IRC(self.queue, self.channel, self.badges, bttv_smiles)
        ircClient.connect(self.host, self.port, self.nickname)
        ircClient.start()


class twitch:
    def __init__(self, queue, pythonFolder):
        log.info("Initializing twitch chat")

        # Reading config from main directory.
        conf_folder = os.path.join(pythonFolder, "conf")
        conf_file = os.path.join(conf_folder, "twitch.cfg")
        config = FlagConfigParser(allow_no_value=True)
        if not os.path.exists(conf_file):
            config.add_section('config')
            config.set('config', 'host', 'irc.twitch.tv')
            config.set('config', 'port', '6667')
            config.set('config', 'channel', 'monstercat')
            config.set('config', 'bttv', 'false')

            config.write(open(conf_file, 'w'))
        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config}

        config.read(conf_file)
        # Checking config file for needed variables
        # host, port, channel = tuple ( [None] * 3 ) ?!?!?!?!
        config_tag = 'config'
        host = config.get_or_default(config_tag, 'host', 'irc.twitch.tv')
        port = int(config.get_or_default(config_tag, 'port', 6667))
        channel = config.get_or_default(config_tag, 'channel', 'monstercat')
        bttv_smiles = config.get_or_default(config_tag, 'bttv', False)
        badges = {}

        # If any of the value are non-existent then exit the programm with error.

        try:
            request = requests.get("http://tmi.twitch.tv/servers?channel="+channel)
            if request.status_code == 200:
                host = random.choice(request.json()['servers']).split(':')[0]
        except:
            log.error("Issue with twitch")
            exit()

        try:
            request = requests.get("https://api.twitch.tv/kraken/chat/{0}/badges".format(channel))
            if request.status_code == 200:
                badges = request.json()
        except:
            log.error("Issue with twitch")
            exit()

        # If any of the value are non-existent then exit the programm with error.
        if (host is None) or (port is None) or (channel is None):
            log.error("Config for twitch is not correct!")
            exit()

        # Creating new thread with queue in place for messaging tranfers
        tw = twThread(queue, host, port, channel, badges, bttv_smiles)
        tw.start()
