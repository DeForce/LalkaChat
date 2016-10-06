# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import datetime
from modules.helpers.parser import FlagConfigParser

DEFAULT_PRIORITY = 20

class logger():
    def __init__(self, conf_folder, **kwargs):
        # Creating filter and replace strings.
        conf_file = os.path.join(conf_folder, "logger.cfg")
        config = FlagConfigParser(allow_no_value=True)
        if not os.path.exists(conf_file):
            config.add_section('config')
            config.set('config', 'logging', 'true')
            config.set('config', 'rotation', 'daily')
            config.set('config', 'file_format', '%Y-%m-%d')
            config.set('config', 'message_date_format', '%Y-%m-%d %H:%M:%S')
            config.write(open(conf_file, 'w'))

        config.read(conf_file)
        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config,
                            'id': config.get_or_default('gui_information', 'id', '10')}

        tag_config = 'config'

        self.format = config.get_or_default(tag_config, 'file_format', '%Y-%m-%d')
        self.ts_format = config.get_or_default(tag_config, 'message_date_format', '%Y-%m-%d %H:%M')
        self.logging = config.get_or_default(tag_config, 'logging', True)
        self.rotation = config.get_or_default(tag_config, 'logging', 'daily')

        self.folder = 'logs'

        self.destination = os.path.join(conf_folder, '..', self.folder)
        if not os.path.exists(self.destination):
            os.makedirs(self.destination)

    def get_message(self, message, queue):
        if message:
            with open('{0}.txt'.format(
                    os.path.join(self.destination, datetime.datetime.now().strftime(self.format))), 'a') as f:
                f.write('[{3}] [{0}] {1}: {2}\n'.format(message['source'].encode('utf-8'),
                                                        message['user'].encode('utf-8'),
                                                        message['text'].encode('utf-8'),
                                                        datetime.datetime.now().strftime(self.ts_format).encode('utf-8')))
            return message
