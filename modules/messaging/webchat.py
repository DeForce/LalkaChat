import ConfigParser
import os
import threading
import json
import Queue
import cherrypy
from cherrypy.lib.static import serve_file
from time import sleep
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from modules.helpers.parser import FlagConfigParser

s_queue = Queue.Queue()


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
    @cherrypy.expose
    # @cherrypy.tools.response_headers([("Expires", '-1')])
    # @cherrypy.tools.response_headers([("Pragma", "no-cache")])
    # @cherrypy.tools.response_headers([("Cache-Control", "private, max-age=0, no-cache, no-store, must-revalidate")])
    def index(self):
        cherrypy.response.headers["Expires"] = -1
        cherrypy.response.headers["Pragma"] = "no-cache"
        cherrypy.response.headers["Cache-Control"] = "private, max-age=0, no-cache, no-store, must-revalidate"
        return serve_file(os.path.join(os.getcwd(), 'http', 'index.html'), 'text/html')

    @cherrypy.expose
    def ws(self):
        # you can access the class instance through
        handler = cherrypy.request.ws_handler


class SocketThread(threading.Thread):
    def __init__(self, host, port, root_folder):
        super(self.__class__, self).__init__()
        self.daemon = True
        self.host = host
        self.port = port
        self.root_folder = root_folder

        cherrypy.config.update({'server.socket_port': int(self.port), 'server.socket_host': self.host,
                                'global': {
                                    'engine.autoreload.on': False
                                }})
        WebChatPlugin(cherrypy.engine).subscribe()
        cherrypy.tools.websocket = WebSocketTool()

    def run(self):
        http_folder = os.path.join(self.root_folder, '..', 'http')
        cherrypy.quickstart(HttpRoot(), '/', config={'/ws': {'tools.websocket.on': True,
                                                             'tools.websocket.handler_cls': WebChatSocketServer},
                                                     '/js': {'tools.staticdir.on': True,
                                                             'tools.staticdir.dir': os.path.join(http_folder, 'js')},
                                                     '/css': {'tools.staticdir.on': True,
                                                              'tools.staticdir.dir': os.path.join(http_folder, 'css')},
                                                     '/img': {'tools.staticdir.on': True,
                                                              'tools.staticdir.dir': os.path.join(http_folder, 'img')}})
                                                     # '/': {'tools.staticdir.on': True,
                                                     #       'tools.staticdir.dir': http_folder,
                                                     #       'tools.staticdir.index': "index.html"}})


class webchat():
    def __init__(self, conf_folder):
        conf_file = os.path.join(conf_folder, "webchat.cfg")

        config = FlagConfigParser(allow_no_value=True)
        if not os.path.exists(conf_file):
            config.add_section('server')
            config.set('server', 'host', '127.0.0.1')
            config.set('server', 'port', '8080')

            config.write(open(conf_file))

        self.conf_params = {'folder': conf_folder, 'file': conf_file,
                            'filename': ''.join(os.path.basename(conf_file).split('.')[:-1]),
                            'parser': config}

        config.read(conf_file)

        tag_server = 'server'
        self.host = config.get_or_default(tag_server, 'host', '127.0.0.1')
        self.port = config.get_or_default(tag_server, 'port', '8080')

        s_thread = SocketThread(self.host, self.port, conf_folder)
        s_thread.start()

        m_thread = MessagingThread()
        m_thread.start()

    def get_message(self, message, queue):
        if message is None:
            # print "webchat received empty message"
            return
        else:
            if 'flags' in message:
                if message['flags'] == 'hidden':
                    return message
            s_queue.put(message)
            return message
