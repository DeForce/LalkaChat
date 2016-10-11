# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import logging
import os
import random
import re
from modules.helpers.parser import self_heal
from modules.helpers.modules import MessagingModule

DEFAULT_PRIORITY = 10
log = logging.getLogger('c2b')


def twitch_replace_indexes(filter_name, text, filter_size, replace_size, emotes_list):
    emotes = []
    message_index_list = [m.start() for m in re.finditer(filter_name, text)]

    offset = replace_size - filter_size
    for emote_data in emotes_list:
        emote = {'emote_id': emote_data['emote_id'],
                 'emote_pos': []}
        for emote_pos in emote_data['emote_pos']:
            e_start, e_end = emote_pos.split('-')
            mod_offset = 0
            for index, item in enumerate(message_index_list):
                if item < int(e_start):
                    mod_offset = offset * (index + 1)
            emote['emote_pos'].append('{0}-{1}'.format(int(e_start) + mod_offset,
                                                       int(e_end) + mod_offset))
        emotes.append(emote)
    return emotes


class c2b(MessagingModule):
    def __init__(self, conf_folder, **kwargs):
        MessagingModule.__init__(self)
        # Creating filter and replace strings.
        conf_file = os.path.join(conf_folder, "c2b.cfg")
        conf_dict = [
            {'gui_information': {
                'category': 'messaging',
                'id': DEFAULT_PRIORITY}},
            {'config__gui': {
                'for': 'config',
                'addable': 'true',
                'view': 'list_dual'}},
            {'config': {}}
        ]

        config = self_heal(conf_file, conf_dict)
        self._conf_params = {'folder': conf_folder, 'file': conf_file,
                             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                             'parser': config,
                             'id': config.get('gui_information', 'id')}

        tag_config = 'config'
        self.f_items = []
        for param, value in config.items(tag_config):
            f_item = {'filter': param.decode('utf-8'), 'replace': value.split('/')}
            f_item['replace'] = [item.strip().decode('utf-8') for item in f_item['replace']]
            self.f_items.append(f_item)

    def process_message(self, message, queue, **kwargs):
        # Replacing the message if needed.
        # Please do the needful
        if message:
            if 'command' in message:
                return message
            for replace in self.f_items:
                if replace['filter'] in message['text']:
                    replace_word = random.choice(replace['replace'])
                    # Fix twitch emoticons if any
                    if message['source'] == 'tw':
                        message['emotes'] = twitch_replace_indexes(replace['filter'], message['text'],
                                                                   len(replace['filter']), len(replace_word),
                                                                   message.get('emotes', []))
                    message['text'] = message['text'].replace(replace['filter'], replace_word)
            return message
