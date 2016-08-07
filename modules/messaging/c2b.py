# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import ConfigParser
import random
import re
from modules.helpers.parser import FlagConfigParser


class c2b:
    def __init__(self, conf_folder):
        # Creating filter and replace strings.
        conf_file = os.path.join(conf_folder, "c2b.cfg")

        config = FlagConfigParser(allow_no_value=True)

        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config}

        config.read(conf_file)
        tag_config = 'config'
        self.f_items = []
        for item in config.get_items(tag_config):
            f_item = {'filter': item[0].decode('utf-8'), 'replace': item[1].split('/')}
            f_item['replace'] = map(lambda x: x.strip().decode('utf-8'), f_item['replace'])
            self.f_items.append(f_item)

    def get_message(self, message, queue):
        # Replacing the message if needed.
        # Please do the needful
        if message is None:
            # print "C2B recieved empty message"
            return
        else:
            for replace in self.f_items:
                match = re.search(u'({0})'.format(replace['filter']), message['text'])
                if match:
                    message['text'] = message['text'].replace(replace['filter'],
                                                              random.choice(replace['replace']))
            return message
