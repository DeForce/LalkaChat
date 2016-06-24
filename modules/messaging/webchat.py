import ConfigParser
import os
import threading
import json
import Queue
import cherrypy
from cherrypy.lib.static import serve_file
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket

s_queue = Queue.Queue()


class MessagingThread(threading.Thread):
    def __init__(self, ws):
        super(self.__class__, self).__init__()
        self.ws = ws

    def run(self):
        while True:
            message = s_queue.get()
            cherrypy.engine.publish('websocket-broadcast', json.dumps(message))


class WebChatSocketServer(WebSocket):
    def __init__(self, sock, protocols=None, extensions=None, environ=None, heartbeat_freq=None):
        super(self.__class__, self).__init__(sock, protocols=None, extensions=None, environ=None, heartbeat_freq=None)
        thread = MessagingThread(self)
        thread.start()
        self.clients = []

    def opened(self):
        cherrypy.engine.publish('add-client', self.peer_address, self)

    def closed(self, code, reason=None):
        cherrypy.engine.publish('del-client', self.peer_address, self)

    def received_message(self, message):
        print message


class WebChatPlugin(WebSocketPlugin):
    def __init__(self, bus):
        WebSocketPlugin.__init__(self, bus)
        self.clients = []

    def start(self):
        WebSocketPlugin.start(self)
        self.bus.subscribe('add-client', self.add_client)
        self.bus.subscribe('del-client', self.del_client)

    def stop(self):
        WebSocketPlugin.stop(self)
        self.bus.unsubscribe('add-client', self.add_client)
        self.bus.unsubscribe('del-client', self.del_client)

    def add_client(self, addr, websocket):
        self.clients.append({'ip': addr[0], 'port': addr[1], 'websocket': websocket})

    def del_client(self, addr):
        self.clients.remove({'ip': addr[0], 'port': addr[1]})


class HttpRoot(object):
    @cherrypy.expose
    def index(self):
        print os.path.join(os.getcwd(), 'http', 'index.html')
        return serve_file(os.path.join(os.getcwd(), 'http', 'index.html'), 'text/html')

    @cherrypy.expose
    def ws(self):
        # you can access the class instance through
        handler = cherrypy.request.ws_handler


class SocketThread(threading.Thread):
    def __init__(self, host, port):
        super(self.__class__, self).__init__()
        self.host = host
        self.port = port

        cherrypy.config.update({'server.socket_port': int(self.port), 'server.socket_host': self.host,
                                'global': {
                                    'engine.autoreload.on': False
                                }})
        WebChatPlugin(cherrypy.engine).subscribe()
        cherrypy.tools.websocket = WebSocketTool()

    def run(self):
        # cherrypy.quickstart(HttpRoot(), '/', config={'/ws': {'tools.websocket.on': True,
        #                                                      'tools.websocket.handler_cls': WebChatSocketServer},
        #                                              '/': {'tools.staticdir.on': True,
        #                                                    'tools.staticdir.root': os.path.join(os.getcwd(), 'http'),
        #                                                    'tools.staticdir.dir': os.path.join(os.getcwd(), 'http'),
        #                                                    'tools.staticdir.index': "index.html",
        #                                                    'tools.staticdir.debug': True,
        #                                                    'log.screen': True}})

        cherrypy.quickstart(HttpRoot(), '/', config={'/ws': {'tools.websocket.on': True,
                                                             'tools.websocket.handler_cls': WebChatSocketServer},
                                                     '/js': {'tools.staticdir.on': True,
                                                             'tools.staticdir.dir': os.path.join(os.getcwd(),
                                                                                                 'http', 'js')},
                                                     '/css': {'tools.staticdir.on': True,
                                                              'tools.staticdir.dir': os.path.join(os.getcwd(),
                                                                                                  'http', 'css')},
                                                     '/img': {'tools.staticdir.on': True,
                                                              'tools.staticdir.dir': os.path.join(os.getcwd(),
                                                                                                  'http', 'img')}})


class webchat():
    def __init__(self, conf_folder):
        conf_file = os.path.join(conf_folder, "webchat.cfg")

        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(conf_file)

        tag_server = 'server'
        for item in config.items(tag_server):
            if item[0] == 'host':
                self.host = item[1]
            if item[0] == 'port':
                self.port = item[1]

        s_thread = SocketThread(self.host, self.port)
        s_thread.start()

    def get_message(self, message):
        if message is None:
            # print "webchat received empty message"
            return
        else:
            if 'flags' in message:
                if message['flags'] == 'hidden':
                    return message
            s_queue.put(message)
            return message
