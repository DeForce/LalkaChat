SOURCE = 'sy'
SOURCE_USER = 'System'
SOURCE_ICON = '/img/sources/lalka_cup.png'


def system_message(message, queue, source=SOURCE, icon=SOURCE_ICON, from_user=SOURCE_USER, ignore_levels=True):
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
