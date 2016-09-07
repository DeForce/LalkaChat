from distutils.core import setup

setup(
    name='LalkaChat',
    version='0.0.1',
    packages=['', 'modules', 'modules.helpers', 'modules.messaging'],
    requires=['requests', 'cherrypy', 'ws4py', 'irc', 'wxpython'],
    url='https://github.com/DeForce/multichat_python',
    license='',
    author='CzT/DeForce',
    author_email='vlad@czt.lv',
    description=''
)
