import os
import threading
import json
import Queue
import cherrypy
import logging
from cherrypy.lib.static import serve_file
from time import sleep
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from modules.helpers.parser import FlagConfigParser

DEFAULT_PRIORITY = 9001
s_queue = Queue.Queue()
logging.getLogger('ws4py').setLevel(logging.ERROR)
log = logging.getLogger('webchat')


class MessagingThread(threading.Thread):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.daemon = True

    def run(self):
        while True:
            message = s_queue.get()
            cherrypy.engine.publish('add-history', message)
            cherrypy.engine.publish('websocket-broadcast', json.dumps(message))


class FireFirstMessages(threading.Thread):
    def __init__(self, ws, history):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.ws = ws
        self.history = history

    def run(self):
        sleep(0.1)
        for item in self.history:
            self.ws.send(json.dumps(item))


class WebChatSocketServer(WebSocket):
    def __init__(self, sock, protocols=None, extensions=None, environ=None, heartbeat_freq=None):
        super(self.__class__, self).__init__(sock)
        self.clients = []

    def opened(self):
        cherrypy.engine.publish('add-client', self.peer_address, self)
        send_history = FireFirstMessages(self, cherrypy.engine.publish('get-history')[0])
        send_history.start()

    def closed(self, code, reason=None):
        cherrypy.engine.publish('del-client', self.peer_address)


class WebChatPlugin(WebSocketPlugin):
    def __init__(self, bus):
        WebSocketPlugin.__init__(self, bus)
        self.clients = []
        self.history = []
        self.history_size = 10

    def start(self):
        WebSocketPlugin.start(self)
        self.bus.subscribe('add-client', self.add_client)
        self.bus.subscribe('del-client', self.del_client)
        self.bus.subscribe('add-history', self.add_history)
        self.bus.subscribe('get-history', self.get_history)

    def stop(self):
        WebSocketPlugin.stop(self)
        self.bus.unsubscribe('add-client', self.add_client)
        self.bus.unsubscribe('del-client', self.del_client)
        self.bus.unsubscribe('add-history', self.add_history)
        self.bus.unsubscribe('get-history', self.get_history)

    def add_client(self, addr, websocket):
        self.clients.append({'ip': addr[0], 'port': addr[1], 'websocket': websocket})

    def del_client(self, addr):
        try:
            self.clients.remove({'ip': addr[0], 'port': addr[1]})
        except:
            pass

    def add_history(self, message):
        self.history.append(message)
        if len(self.history) > self.history_size:
            self.history.pop(0)

    def get_history(self):
        return self.history


class HttpRoot(object):
    def __init__(self, http_folder):
        object.__init__(self)
        self.http_folder = http_folder

    @cherrypy.expose
    def index(self):
        cherrypy.response.headers["Expires"] = -1
        cherrypy.response.headers["Pragma"] = "no-cache"
        cherrypy.response.headers["Cache-Control"] = "private, max-age=0, no-cache, no-store, must-revalidate"
        return serve_file(os.path.join(self.http_folder, 'index.html'), 'text/html')

    @cherrypy.expose
    def ws(self):
        # you can access the class instance through
        handler = cherrypy.request.ws_handler


class SocketThread(threading.Thread):
    def __init__(self, host, port, root_folder, **kwargs):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.host = host
        self.port = port
        self.root_folder = root_folder
        self.style = kwargs.pop('style')

        cherrypy.config.update({'server.socket_port': int(self.port), 'server.socket_host': self.host,
                                'engine.autoreload.on': False
                                })
        WebChatPlugin(cherrypy.engine).subscribe()
        cherrypy.tools.websocket = WebSocketTool()

    def run(self):
        http_folder = os.path.join(self.root_folder, '..', 'http', self.style)
        cherrypy.log.access_file = ''
        cherrypy.log.error_file = ''
        cherrypy.log.screen = False

        # Removing Access logs
        cherrypy.log.access_log.propagate = False
        cherrypy.log.error_log.setLevel(logging.ERROR)

        cherrypy.quickstart(HttpRoot(http_folder), '/',
                            config={'/ws': {'tools.websocket.on': True,
                                            'tools.websocket.handler_cls': WebChatSocketServer},
                                    '/js': {'tools.staticdir.on': True,
                                            'tools.staticdir.dir': os.path.join(http_folder, 'js')},
                                    '/css': {'tools.staticdir.on': True,
                                             'tools.staticdir.dir': os.path.join(http_folder, 'css')},
                                    '/img': {'tools.staticdir.on': True,
                                             'tools.staticdir.dir': os.path.join(http_folder, 'img')}})


class webchat():
    def __init__(self, conf_folder, **kwargs):
        conf_file = os.path.join(conf_folder, "webchat.cfg")
        root_folder = kwargs.get('root_folder')
        http_folder = 'http'

        config = FlagConfigParser(allow_no_value=True)
        if not os.path.exists(conf_file):
            config.add_section('gui_information')
            config.set('gui_information', 'category', 'main')

            config.add_section('style__gui')
            config.set('style__gui', 'for', 'style')
            config.set('style__gui', 'view', 'choose_single')
            config.set('style__gui', 'check_type', 'dir')
            config.set('style__gui', 'check', 'http')

            config.add_section('style')
            config.set('style', 'czt')

            config.add_section('server')
            config.set('server', 'host', '127.0.0.1')
            config.set('server', 'port', '8080')

            config.write(open(conf_file, 'w'))

        config.read(conf_file)
        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config,
                            'id': config.get_or_default('gui_information', 'id', DEFAULT_PRIORITY)}

        tag_server = 'server'
        host = config.get_or_default(tag_server, 'host', '127.0.0.1')
        port = config.get_or_default(tag_server, 'port', '8080')

        # Fallback if style folder not found
        fallback_style = 'czt'
        if len(config.items('style')) > 0:
            style, null_element = config.items('style')[0]
            path = os.path.abspath(os.path.join(root_folder, http_folder, style))
            if not os.path.exists(path):
                style = fallback_style
        else:
            style = fallback_style

        self.conf_params['port'] = port

        s_thread = SocketThread(host, port, conf_folder, style=style)
        s_thread.start()

        m_thread = MessagingThread()
        m_thread.start()

    def get_message(self, message, queue):
        if message:
            if 'flags' in message:
                if message['flags'] == 'hidden':
                    return message
            s_queue.put(message)
            return message
