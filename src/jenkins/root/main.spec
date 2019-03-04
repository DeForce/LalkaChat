# -*- mode: python -*-

import sys
import os.path

sys.modules['FixTk'] = None
block_cipher = None

specpath = os.path.dirname(os.path.abspath(SPEC))

data = [
    ('modules', 'modules'),
    ('img', 'img'),
    ('scripts', 'scripts'),
    ('translations', 'translations'),
    ('default_branch', '.'),
]

a = Analysis(['main.py'],
             pathex=['./'],
             binaries=[],
             datas=data,
             hiddenimports=['cherrypy',
                            'ws4py',
                            'requests',
                            'irc',
                            'configparser',
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
             hookspath=['.'],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
             win_no_prefer_redirects=True,
             win_private_assemblies=True,
             cipher=block_cipher)

if not os.environ.get("PYINSTALLER_CEFPYTHON3_HOOK_SUCCEEDED", None):
    raise SystemExit("Error: Pyinstaller hook-cefpython3.py script was "
                     "not executed or it failed")

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='LalkaChat',
          debug=False,
          strip=False,
          upx=True,
          console=True,
          icon=os.path.join(specpath, "img", 'lalka_cup.ico'))
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='main')
