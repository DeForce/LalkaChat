# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import re
from collections import OrderedDict

from modules.helper.parser import self_heal
from modules.helper.modules import MessagingModule


class mentions(MessagingModule):
    def __init__(self, conf_folder, **kwargs):
        MessagingModule.__init__(self)
        # Creating filter and replace strings.
        conf_file = os.path.join(conf_folder, "mentions.cfg")
        conf_dict = OrderedDict()
        conf_dict['gui_information'] = {'category': 'messaging'}
        conf_dict['mentions'] = {}
        conf_dict['address'] = {}

        conf_gui = {
            'mentions': {
                'addable': 'true',
                'view': 'list'},
            'address': {
                'addable': 'true',
                'view': 'list'},
            'non_dynamic': ['mentions.*', 'address.*']}
        config = self_heal(conf_file, conf_dict)
        self._conf_params = {'folder': conf_folder, 'file': conf_file,
                             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                             'parser': config,
                             'config': conf_dict,
                             'gui': conf_gui}
        mention_tag = 'mentions'
        address_tag = 'address'
        if config.has_section(mention_tag):
            self.mentions = [item for item, value in config.items(mention_tag)]
        else:
            self.mentions = []

        if config.has_section(address_tag):
            self.addresses = [item.decode('utf-8').lower() for item, value in config.items(address_tag)]
        else:
            self.addresses = []

    def process_message(self, message, queue, **kwargs):
        # Replacing the message if needed.
        # Please do the needful
        if message:
            if 'command' in message:
                return message
            for mention in self.mentions:
                if re.search(mention, message['text'].lower()):
                    message['mention'] = True

            for address in self.addresses:
                if re.match(address, message['text'].lower()):
                    message['pm'] = True

            if 'mention' in message and 'pm' in message:
                message.pop('mention')

            return message
