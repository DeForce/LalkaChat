# coding=utf-8
# Copyright (C) 2016   CzT/Vladislav Ivanov
import collections
import locale
import logging
import random
from functools import reduce

import re
import os
import string
import sys
import requests
import semantic_version
import yaml

if hasattr(sys, 'frozen'):
    PYTHON_FOLDER = os.path.dirname(sys.executable)
else:
    PYTHON_FOLDER = os.path.dirname(os.path.abspath('__file__'))
TRANSLATION_FOLDER = os.path.join(PYTHON_FOLDER, "translations")
CONF_FOLDER = os.path.join(PYTHON_FOLDER, "conf")
MODULE_FOLDER = os.path.join(PYTHON_FOLDER, "modules")
MAIN_CONF_FILE = os.path.join(CONF_FOLDER, "config.cfg")
HTTP_FOLDER = os.path.join(PYTHON_FOLDER, "http")

VERSION = '0.4.0'
SOURCE_REPO_URL = 'https://github.com/DeForce/LalkaChat'

GUI_TAG = 'gui'
WINDOWS = True if sys.platform == 'win32' else False

LOG_FOLDER = os.path.join(PYTHON_FOLDER, "logs")
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)
LOG_FILE = os.path.join(LOG_FOLDER, 'chat_log.log')
LOG_FORMAT = logging.Formatter("%(asctime)s [%(threadName) s%(name)s] [%(levelname)s]  %(message)s")

log = logging.getLogger('system')

THREADS = 2

SOURCE = 'sy'
SOURCE_USER = 'System'
SOURCE_ICON = '/img/sources/lalka_cup.png'

SECRETS_FILE = 'secrets.yaml'

NO_VIEWERS = 'N/A'

IGNORED_TYPES = ['command', 'system_message']
TRANSLATIONS = {}
SPLIT_TRANSLATION = '='
MODULE_KEY = '.'
EMOTE_FORMAT = u':emote;{0}:'
TRANSLATION_FILETYPE = '.key'
DEFAULT_LANGUAGE = 'en'
ACTIVE_LANGUAGE = None

REPLACE_SYMBOLS = '<>'

LANGUAGE_DICT = {
    'en_US': 'en',
    'en_GB': 'en',
    'ru_RU': 'ru'
}


def system_message(message, queue, source=SOURCE,
                   icon=SOURCE_ICON, from_user=SOURCE_USER, category='system'):
    queue.put({'source': source,
               'source_icon': icon,
               'user': from_user,
               'text': cleanup_tags(message),
               'category': category,
               'type': 'system_message'})


class ModuleLoadException(Exception):
    def __init__(self, message, *args: object):
        super().__init__(*args)
        self.message = message

    def __str__(self):
        return repr(self.message)


class RestApiException(Exception):
    pass


def load_translations_keys(translation_folder, language):
    def load_language(language_folder):
        files_list = [r_item for r_item in os.listdir(language_folder) if r_item.endswith(TRANSLATION_FILETYPE)]
        for f_file in files_list:
            with open(os.path.join(language_folder, f_file), encoding='utf-8') as r_file:
                for line in r_file.readlines():
                    log.debug(line.strip())
                    if line.strip():
                        key, value = map(str.strip, line.strip().split(SPLIT_TRANSLATION))
                        if key not in TRANSLATIONS:
                            TRANSLATIONS[key] = value
    language = language.simple().lower()
    dir_list = [f_item for f_item in os.listdir(translation_folder)
                if os.path.isdir(os.path.join(translation_folder, f_item))]
    languages_to_load = [language, DEFAULT_LANGUAGE]
    global ACTIVE_LANGUAGE
    ACTIVE_LANGUAGE = language
    for language_item in languages_to_load:
        if language_item in dir_list:
            load_language(os.path.join(translation_folder, language_item))
        else:
            log.warning("Unable to load language %s", language_item)


def find_key_translation(item, language=ACTIVE_LANGUAGE):
    translation = TRANSLATIONS.get(item)
    if translation is None:
        split_item = [f_item for f_item in item.split(MODULE_KEY) if f_item != '*']
        if len(split_item) > 1:
            wildcard_item = MODULE_KEY.join(split_item[1:])
            return find_key_translation(f'*{MODULE_KEY}{wildcard_item}')
        else:
            if language == ACTIVE_LANGUAGE:
                return find_key_translation(item, language=DEFAULT_LANGUAGE)
            else:
                return item
    return translation


def get_key_from_translation(translation):
    for key, value in TRANSLATIONS.items():
        if value == translation:
            return key
    return translation


def translate_key(item):
    item_no_flags = item.split('/')[0]
    old_item = item_no_flags

    translation = find_key_translation(item_no_flags)

    if re.match('\*', translation):
        return old_item
    return translation.replace('\\n', '\n')


def cleanup_tags(message):
    for symbol in REPLACE_SYMBOLS:
        message.replace(symbol, f'\{symbol}')
    return message


def random_string(length):
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(length))


def get_update(sem_version):
    github_url = "https://api.github.com/repos/DeForce/LalkaChat/releases"
    try:
        update_json = requests.get(github_url, timeout=1)
        if update_json.status_code == 200:
            update = False
            update_url = None
            update_list = update_json.json()
            for update_item in update_list:
                if semantic_version.Version.coerce(update_item['tag_name'].lstrip('v')) > sem_version:
                    update = True
                    update_url = update_item['html_url']
            return update, update_url
    except Exception as exc:
        log.info("Got exception: %s", exc)
    return False, None


def get_language():
    local_name, local_encoding = locale.getdefaultlocale()
    return LANGUAGE_DICT.get(local_name, 'en')


def get_languages():
    item_path = os.path.join(PYTHON_FOLDER, 'translations')
    return [translate_key(item) for item in os.listdir(item_path)
            if os.path.isdir(os.path.join(item_path, item))]


def get_key(*args):
    return MODULE_KEY.join(args)


def deep_get_from_dict(dictionary, *keys):
    return reduce(lambda d, key: d.get(key, None) if isinstance(d, collections.Mapping) else None, keys, dictionary)


def get_secret(path):
    path_list = path.split('.')

    with open(SECRETS_FILE, 'r') as secrets_file:
        data = yaml.safe_load(secrets_file)

    return deep_get_from_dict(data, *path_list)

def get_wx_parent(item):
    if item.GrandParent:
        return get_wx_parent(item.GrandParent)
    return item
