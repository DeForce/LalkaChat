#!/usr/bin/env python
import Queue
import logging

import time

from modules.chat.sc2tv import sc2tv, FsSystemMessage

BASECONFIG = {
    'config': {
        'config': {
            'channels_list': ['CzT']
        }
    }
}

logging.basicConfig(level=logging.getLevelName('DEBUG'))


def validate_message(message):
    if 'join_success' in message.text:
        logging.info('Connection to peka2.tv is successful')

        return True
    return False

if __name__ == '__main__':
    queue = Queue.Queue()

    sc2tv_class = sc2tv(conf_params=BASECONFIG, queue=queue)
    sc2tv_class.load_module(loaded_modules={})

    channel = sc2tv_class.channels[sc2tv_class.channels.keys()[0]]
    try:
        tries = 10
        while tries:
            message = queue.get(timeout=10)  # type: FsSystemMessage
            if validate_message(message):
                exit(0)
            tries -= 1
    except Queue.Empty:
        logging.error('Connection failed')
    exit(1)
