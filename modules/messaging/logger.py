# This Python file uses the following encoding: utf-8
# -*- coding: utf-8 -*-
import os
import ConfigParser
import datetime


class logger():
    def __init__(self, conf_folder):
        # Creating filter and replace strings.
        conf_file = os.path.join(conf_folder, "logger.cfg")

        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(conf_file)
        tag_config = 'config'

        self.format = '%Y-%m-%d'
        self.ts_format = '%Y-%m-%d %H:%M'
        self.logging = True
        self.rotation = 'daily'

        self.folder = 'logs'

        for item in config.items(tag_config):
            if item[0] == 'logging':
                if item[0] == 'true':
                    self.logging = True
                else:
                    self.logging = False
            elif item[0] == 'rotation':
                if item[1] == 'daily':
                    self.rotation = 'daily'
            elif item[0] == 'file_format':
                self.format = item[1]
            elif item[0] == 'message_date_format':
                self.ts_format = item[1]

        self.destination = os.path.join(conf_folder, '..', self.folder)
        if not os.path.exists(self.destination):
            os.makedirs(self.destination)

    def get_message(self, message, queue):
        if message is None:
            # print "Logger recieved empty message"
            return
        else:
            with open('{0}.txt'.format(
                    os.path.join(self.destination, datetime.datetime.now().strftime(self.format))), 'a') as f:
                f.write('[{3}] [{0}] {1}: {2}\n'.format(message['source'], message['user'], message['text'],
                                                        datetime.datetime.now().strftime(self.ts_format)))
            return message
