# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import re
from collections import OrderedDict

from modules.helper.parser import self_heal
from modules.helper.modules import MessagingModule
from modules.helper.system import IGNORED_TYPES


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
                'view': 'list'}}
        config = self_heal(conf_file, conf_dict)
        self._conf_params = {'folder': conf_folder, 'file': conf_file,
                             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                             'parser': config,
                             'config': conf_dict,
                             'gui': conf_gui}

    def process_message(self, message, queue, **kwargs):
        # Replacing the message if needed.
        # Please do the needful
        if message:
            if message['type'] in IGNORED_TYPES:
                return message

            for mention, value in self._conf_params['config']['mentions'].iteritems():
                if re.search(mention, message['text'].lower()):
                    message['mention'] = True
                    break

            for address, value in self._conf_params['config']['address'].iteritems():
                if re.match(address, message['text'].lower()):
                    message['pm'] = True
                    break

            if 'mention' in message and 'pm' in message:
                message.pop('mention')

            return message
