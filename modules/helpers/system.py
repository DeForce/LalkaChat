SOURCE = 'sy'
SOURCE_USER = 'System'
SOURCE_ICON = '/img/sources/lalka_cup.png'


def system_message(message, queue, source=SOURCE, icon=SOURCE_ICON, from_user=SOURCE_USER):
    queue.put({'source': source,
               'source_icon': icon,
               'user': from_user,
               'text': message})
