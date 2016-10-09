from distutils.core import setup

setup(
    name='LalkaChat',
    version='0.2.0',
    packages=['', 'modules', 'modules.helpers', 'modules.messaging'],
    requires=['requests', 'cherrypy', 'ws4py', 'irc', 'wxpython', 'cefpython3'],
    url='https://github.com/DeForce/LalkaChat',
    license='',
    author='CzT/DeForce',
    author_email='vlad@czt.lv',
    description=''
)
