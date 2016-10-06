# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import re
from modules.helpers.parser import FlagConfigParser


class mentions():
    def __init__(self, conf_folder, **kwargs):
        # Creating filter and replace strings.
        conf_file = os.path.join(conf_folder, "mentions.cfg")
        config = FlagConfigParser(allow_no_value=True)
        if not os.path.exists(conf_file):
            config.add_section('config')
            config.add_section('config_gui')
            config.set('config_gui', 'for', 'mentions, address')
            config.set('config_gui', 'view', 'list')
            config.set('config_gui', 'addable', 'true')
            config.add_section('mentions')
            config.add_section('address')

            config.write(open(conf_file, 'w'))
        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config}

        config.read(conf_file)
        mention_tag = 'mentions'
        address_tag = 'address'
        if config.has_section(mention_tag):
            self.mentions = map(lambda x: x[0], config.get_items(mention_tag))
        else:
            self.mentions = {}

        if config.has_section(address_tag):
            self.addresses = map(lambda x: x[0], config.get_items(address_tag))
        else:
            self.addresses = {}

    def get_message(self, message, queue):
        # Replacing the message if needed.
        # Please do the needful
        if message is None:
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
