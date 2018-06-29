# -*- mode: python -*-

import sys

sys.modules['FixTk'] = None
block_cipher = None

data = [
    ('modules', 'modules'),
    ('img', 'img'),
    ('scripts', 'scripts'),
    ('translations', 'translations'),
    ('libs/windows/locales', 'locales'),
    ('libs/windows/icudt.dll', ''),
    ('libs/windows/subprocess.exe', ''),
]

a = Analysis(['main.py'],
             pathex=['./'],
             binaries=[],
             datas=data,
             hiddenimports=['cherrypy',
                            'ws4py',
                            'requests',
                            'irc',
                            'ConfigParser',
                            'modules.main',
                            'modules.gui',
                            'modules.message_handler',
                            'modules.chat.goodgame',
                            'modules.chat.sc2tv',
                            'modules.chat.twitch',
                            'modules.helper.parser',
                            'modules.helper.system',
                            'modules.messaging.blacklist',
                            'modules.messaging.c2b',
                            'modules.messaging.df',
                            'modules.messaging.levels',
                            'modules.messaging.logger',
                            'modules.messaging.mentions',
                            'modules.messaging.webchat'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='LalkaChat',
          debug=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='main')
