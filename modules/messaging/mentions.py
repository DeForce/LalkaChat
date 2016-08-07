# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import ConfigParser
import re
from modules.helpers.parser import FlagConfigParser

class mentions():
    def __init__(self, conf_folder):
        # Creating filter and replace strings.
        conf_file = os.path.join(conf_folder, "mentions.cfg")
        config = FlagConfigParser(allow_no_value=True)

        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config}

        config.read(conf_file)
        tag_config = 'config'
        self.mentions = []
        self.addresses = []
        for item in config.get_items(tag_config):
            if item[0] == 'mentions':
                mention = item[1].split(',')
                mention = map(lambda x: x.strip().lower().decode('utf-8'), mention)
                map(lambda x: self.mentions.append(x), mention)
            elif item[0] == 'address':
                address = item[1].split(',')
                # address = map(lambda x: x.strip().lower().decode('utf-8'), address)
                address = map(lambda x: x.strip().lower(), address)
                map(lambda x: self.addresses.append(x), address)

    def get_message(self, message, queue):
        # Replacing the message if needed.
        # Please do the needful
        if message is None:
            # print "C2B recieved empty message"
            return
        else:
            for mention in self.mentions:
                if re.search(mention, message['text'].lower()):
                    message['mention'] = True

            for address in self.addresses:
                if re.match('^{0}(,| )'.format(address), message['text'].lower().encode('utf-8')):
                    message['pm'] = True

            if 'mention' in message and 'pm' in message:
                message.pop('mention')

            return message
