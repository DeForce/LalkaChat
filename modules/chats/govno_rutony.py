import random
import threading
import string
import time
import logging
import queue
from modules.helpers.system import SOURCE, SOURCE_ICON, THREADS
from modules.helpers.modules import ChatModule

log = logging.getLogger('govno_rutony')


class MessageThread(threading.Thread):
    def __init__(self, users, message, queue):
        threading.Thread.__init__(self)
        self.users = users
        self.message = message
        self.queue = queue  # type: queue.Queue

    def run(self):
        time.sleep(random.randrange(0, 10000)/10000.0)
        time.sleep(5)
        while True:
            log.info(self.queue.qsize())
            time.sleep(1)
            # self.queue.put({'source': 'tw',
            #                 'source_icon': SOURCE_ICON,
            #                 'user': random.choice(self.users),
            #                 'text': self.message})

            self.queue.put({'source_icon': 'https://www.twitch.tv/favicon.ico',
                            'bttv_emotes': [],
                            'msg_type': 'pubmsg',
                            'text': u'KappaPride Test Kappa test knjHmhm dimaHi twarynaMad {0}'.format(self.message),
                            'emotes': [{'emote_id': u'70886', 'emote_pos': [u'42-51']},
                                       {'emote_id': u'55338', 'emote_pos': [u'0-9']},
                                       {'emote_id': u'25', 'emote_pos': [u'16-20']},
                                       {'emote_id': u'23176', 'emote_pos': [u'27-33']},
                                       {'emote_id': u'17675', 'emote_pos': [u'35-40']}],
                            'source': 'tw',
                            'user': u'CzT1',
                            'badges': [{'url': u'https://static-cdn.jtvnw.net/chat-badges/broadcaster.svg',
                                        'badge': u'broadcaster',
                                        'size': u'1'}]})


class govno_rutony(ChatModule):
    def __init__(self, queue, python_folder, **kwargs):
        ChatModule.__init__(self)
        self.conf_params = {}
        user_count = 10
        digit_count = 10
        users = [''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(digit_count))
                 for user in range(user_count)]

        self.threads = []
        for thread in range(THREADS):
            self.threads.append(MessageThread(users, "Thread {0}".format(thread), queue))
            self.threads[thread].start()
