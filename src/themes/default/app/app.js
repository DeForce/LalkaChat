var Vue = require('vue');
var twemoji = require('twemoji');

(function (WebSocket, Vue) {
    'use strict';

    new Vue({
        el: '#chat-container',
        data: function () {
            var wsUrl = 'ws://' + window.location.host + window.location.pathname + 'ws';
            var messages = [];
            var socket = new WebSocket(wsUrl);

            return {
                messages: messages,
                url: wsUrl,
                socket: socket,
                attempts: 0,
                socketInterval: null,
                messagesClearInterval: -1,
                messagesDecayInterval: -1,
                messagesLimit: 30
            }
        },
        created: function () {
            var self = this;

            self.socket.onmessage = this.onmessage;
            self.socket.onopen = this.onopen;
            self.socket.onclose = this.onclose;

            var style_get = 'chat';
            if(window.location.pathname.indexOf('gui') !== -1) {
                style_get = 'gui'
            }

            self.get('http://' + window.location.host + '/rest/webchat/style/' + style_get, function (err, response) {
                if (err) {
                    console.log('Error: Bad response from server')
                }

                self.messagesClearInterval = response.clear_timer * 1000 || -1;
                if (self.messagesClearInterval > 0) {
                    setInterval(self.clear, 500);
                }

                self.messagesDecayInterval = response.decay_timer * 1000 || -1;
                if (self.messagesDecayInterval > 0) {
                    setInterval(self.decay, 500);
                }

                self.messagesLimit = response.message_limit;
            });
        },
        methods: {
            mouseenter: function (message) {
                message.deleteButton = true;
            },
            mouseleave: function (message) {
                message.deleteButton = false;
            },
            clear: function () {
                var that = this;
                var time = new Date();

                this.messages = this.messages.filter(function (message) {
                    return Math.abs(time - message.time) < that.messagesClearInterval;
                });
            },
            decay: function () {
                var that = this;
                var time = new Date();

                this.messages = this.messages.filter(function (message) {
                    if(message.old) return message;
                    if(Math.abs(time - message.time) > that.messagesDecayInterval) {
                        message.old = true
                    }
                    return message;
                });
            },
            remove: function (message) {
                var index = this.messages.indexOf(message);
                if (index >= 0) {
//                    this.del('http://' + window.location.host + '/rest/webchat/chat/' + message.id, function(err, ok) {});
                    this.messages.splice(index, 1);
                }
            },
            sanitize: function (message) {
                var clean = this.replaceEmotions(message.text, message.emotes);
                if (!clean) this.remove(message);
                return clean;
            },
            replaceEmotions: function (message, emotes) {
                var tw_message = twemoji.parse(message);
                return emotes.reduce(function (m, emote) {
                        var regex = new RegExp(emote.id, 'g');
                        return m.replace(regex, '<img class="smile" src="' + emote.url + '"  alt=""/>')
                    },
                    tw_message);
            },
            removeByIds: function (ids) {
                this.messages = this.messages.filter(function (message) {
                    return ids.indexOf(message.id) < 0;
                });
            },
            removeByUsernames: function (usernames) {
                usernames = usernames.map(function (value) {
                    return value.toLowerCase();
                });

                this.messages = this.messages.filter(function (message) {
                    var user = message.user.toLowerCase();
                    return usernames.indexOf(user) < 0;
                });
            },
            replaceByUsernames: function (usernames, text) {
                var usernames_lc = usernames.map(function (value) {
                    return value.toLowerCase();
                });

                this.messages = this.messages.map(function (message) {
                    var user = message.user.toLowerCase();
                    var index = usernames_lc.indexOf(user);

                    if (index >= 0) {
                        message.text = text;
                        message.emotes = [];
                    }

                    return message;
                });
            },
            replaceByIds: function (ids, text) {
                this.messages = this.messages.map(function (message) {
                    var index = ids.indexOf(message.id);

                    if (index >= 0) {
                        message.text = text;
                        message.emotes = [];
                        message.pm = false;
                    }
                    return message;
                });
            },
            run: function (message) {
                switch (message.command) {
                    case 'reload':
                        window.location.reload();
                        break;
                    case 'remove_by_users':
                        this.removeByUsernames(message.users);
                        break;
                    case 'remove_by_ids':
                        this.removeByIds(message.messages);
                        break;
                    case 'replace_by_users':
                        this.replaceByUsernames(message.users, message.text);
                        break;
                    case 'replace_by_ids':
                        this.replaceByIds(message.messages, message.text);
                        break;
                    default:
                        console.log('Got unknown command ', message.command);
                }
            },
            onmessage: function (event) {
                var message = JSON.parse(event.data);
                if (!message.type)
                    return;

                switch (message.type) {
                    case 'command':
                        this.run(message.payload);
                        break;
                    default:
                        message.payload.time = new Date();
                        message.payload.deleteButton = false;
                        message.payload.old = false;

                        this.messages.push(message.payload);
                        if (this.messages.length > this.messagesLimit) {
                            this.remove(this.messages[0]);
                        }
                }
            },
            onopen: function () {
                this.attempts = 0;
                if (!this.socketInterval) {
                    clearInterval(this.socketInterval);
                    this.socketInterval = null;
                }
            },
            onclose: function () {
                this.socketInterval = setInterval(this.reconnect, 1000);
            },
            reconnect: function () {
                this.attempts++;

                this.socket = new WebSocket(this.url);
            },
            load: function (method, url, callback, data) {
                var xhr = new XMLHttpRequest();
                xhr.onload = function () {
                    if (xhr.responseText) {
                        var obj = JSON.parse(xhr.responseText);
                        callback(null, obj);
                    }
                };
                xhr.onerror = function () {
                    if (xhr.responseText) {
                        var obj = JSON.parse(xhr.responseText);
                        callback(obj);
                    }
                };

                xhr.open(method, url);
                xhr.send(data);
            },
            get: function (url, callback, data) {
                return this.load('GET', url, callback, data);
            },
            post: function (url, data, callback) {
                return this.load('POST', url, callback, data);
            },
            del: function (url, callback) {
                return this.load('DELETE', url, callback);
            }
        },
        filters: {}
    });
})(window.WebSocket, Vue);
