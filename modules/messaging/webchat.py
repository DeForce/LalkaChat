import os
import threading
import json
import Queue
import socket
from collections import OrderedDict

import cherrypy
import logging
from cherrypy.lib.static import serve_file
from time import sleep
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from modules.helper.parser import self_heal
from modules.helper.system import THREADS
from modules.helper.modules import MessagingModule
from gui import MODULE_KEY

DEFAULT_PRIORITY = 9001
HISTORY_SIZE = 20
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
            cherrypy.engine.publish('websocket-broadcast', json.dumps(message))
            if 'command' not in message:
                cherrypy.engine.publish('add-history', message)


class FireFirstMessages(threading.Thread):
    def __init__(self, ws, history):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.ws = ws
        self.history = history

    def run(self):
        sleep(0.1)
        for item in self.history:
            if item:
                self.ws.send(json.dumps(item))


class WebChatSocketServer(WebSocket):
    def __init__(self, sock, protocols=None, extensions=None, environ=None, heartbeat_freq=None):
        WebSocket.__init__(self, sock)
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
        self.history_size = HISTORY_SIZE

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
        message['history'] = True
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
        http_folder = self.style
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


def socket_open(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    return sock.connect_ex((host, int(port)))


class webchat(MessagingModule):
    def __init__(self, conf_folder, **kwargs):
        MessagingModule.__init__(self)
        main_settings = kwargs.get('main_settings')
        conf_file = os.path.join(conf_folder, "webchat.cfg")
        conf_dict = OrderedDict()
        conf_dict['gui_information'] = {
            'category': 'main',
            'id': DEFAULT_PRIORITY
        }
        conf_dict['server'] = OrderedDict()
        conf_dict['server']['host'] = '127.0.0.1'
        conf_dict['server']['port'] = '8080'
        conf_gui = {'non_dynamic': ['server.*']}

        config = self_heal(conf_file, conf_dict)

        tag_server = 'server'
        host = config.get(tag_server, 'host')
        port = config.get(tag_server, 'port')
        style = main_settings['http_folder']

        self._conf_params = {'folder': conf_folder, 'file': conf_file,
                             'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                             'parser': config,
                             'id': config.get('gui_information', 'id'),
                             'config': conf_dict,
                             'gui': conf_gui,
                             'port': port}
        if socket_open(host, port):
            s_thread = SocketThread(host, port, conf_folder, style=style)
            s_thread.start()

            self.message_threads = []
            for thread in range(THREADS+5):
                self.message_threads.append(MessagingThread())
                self.message_threads[thread].start()
        else:
            log.error("Port is already used, please change webchat port")

    def gui_button_press(self, gui_module, event, list_keys):
        log.debug("Received button press for id {0}".format(event.GetId()))
        keys = MODULE_KEY.join(list_keys)
        if keys == 'menu.reload':
            gui_module.queue.put({'command': 'reload'})
        event.Skip()

    def process_message(self, message, queue, **kwargs):
        if message:
            if 'flags' in message:
                if message['flags'] == 'hidden':
                    return message
            s_queue.put(message)
            return message
