import logging
import re
import os

log = logging.getLogger('system')

SOURCE = 'sy'
SOURCE_USER = 'System'
SOURCE_ICON = '/img/sources/lalka_cup.png'

TRANSLATIONS = {}
SPLIT_TRANSLATION = '='
MODULE_KEY = '.'
TRANSLATION_FILETYPE = '.key'
DEFAULT_LANGUAGE = 'en'
ACTIVE_LANGUAGE = None


def system_message(message, queue, source=SOURCE, icon=SOURCE_ICON, from_user=SOURCE_USER):
    queue.put({'source': source,
               'source_icon': icon,
               'user': from_user,
               'text': message,
               'system_msg': True})


class ModuleLoadException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


def load_translations_keys(translation_folder, language):
    def load_language(language_folder):
        files_list = [f_item for f_item in os.listdir(language_folder) if f_item.endswith(TRANSLATION_FILETYPE)]
        for f_file in files_list:
            with open(os.path.join(language_folder, f_file)) as r_file:
                for line in r_file.readlines():
                    log.debug(line)
                    if line.strip():
                        key, value = map(str.strip, line.strip().split(SPLIT_TRANSLATION))
                        if key not in TRANSLATIONS:
                            TRANSLATIONS[key] = value
    language = language.lower()
    dir_list = [f_item for f_item in os.listdir(translation_folder)
                if os.path.isdir(os.path.join(translation_folder, f_item))]
    languages_to_load = [language, DEFAULT_LANGUAGE]
    global ACTIVE_LANGUAGE
    ACTIVE_LANGUAGE = language
    for language_item in languages_to_load:
        if language_item in dir_list:
            load_language(os.path.join(translation_folder, language_item))
        else:
            log.warning("Unable to load language {0}".format(language_item))


def find_key_translation(item, length=0, wildcard=1):
    translation = TRANSLATIONS.get(item, item)
    if item == translation:
        if wildcard < length:
            translation = find_key_translation(MODULE_KEY.join(['*'] + item.split(MODULE_KEY)[-wildcard:]),
                                               length=length, wildcard=wildcard+1)
        else:
            return translation
    return translation


def get_key_from_translation(translation):
    for key, value in TRANSLATIONS.items():
        if value == translation:
            return key
    return translation


def translate_key(item):
    item_no_flags = item.split('/')[0]
    old_item = item_no_flags

    translation = find_key_translation(item_no_flags, length=len(item_no_flags.split(MODULE_KEY)))

    if re.match('\*', translation):
        return old_item
    return translation.decode('utf-8')


def translate(text):
    pass
