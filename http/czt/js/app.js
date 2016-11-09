(function (WebSocket, Vue, Sanitizer) {
    'use strict';

    var viewModel = new Vue({
        el: '#chat-container',
        data: function () {
            var wsUrl = 'ws://' + window.location.host + '/ws';
            var messages = [];
            var socket = new WebSocket(wsUrl);

            return {
                messages: messages,
                url: wsUrl,
                socket: socket,
                attempts: 0,
                socketInterval: null,
                messagesInterval: -1
            }
        },
        created: function () {
            this.socket.onmessage = this.onmessage;
            this.socket.onopen = this.onopen;
            this.socket.onclose = this.onclose;
            if (this.messagesInterval > 0) {
                setInterval(this.clear, 500);
            }
        },
        methods: {
            clear: function () {
                var that = this;
                var time = new Date();

                this.messages = this.messages.filter(function (message) {
                    return Math.abs(time - message.time) < that.messagesInterval;
                });
            },
            sanitize: function (message) {
                var html = '';

                switch (message.source) {
                    case 'tw':
                        html = this.replaceTwitchEmotions(message.text, message.emotes);

                        if (message.hasOwnProperty('bttv_emotes')) {
                            html = this.replaceBttvEmoticons(html, message.bttv_emotes);
                        }
                        break;
                    case 'gg':
                    case 'fs':
                        html = this.replaceDefaultEmotions(message.text, message.emotes);
                        break;
                    default:
                        html = message.text;
                        break;
                }

                return Sanitizer.sanitize(html);
            },
            replaceTwitchEmotions: function (message, emotes) {
                if (!emotes || emotes.length <= 0) {
                    return message;
                }
                var placesToReplace = [];
                for (var emote in emotes) {
                    if (Array.isArray(emotes[emote]['emote_pos'])) {
                        for (var i = 0; i < emotes[emote]['emote_pos'].length; ++i) {
                            var range = emotes[emote]['emote_pos'][i];
                            var rangeParts = range.split('-');
                            placesToReplace.push({
                                "emote_id": emotes[emote]['emote_id'],
                                "from": parseInt(rangeParts[0]),
                                "to": parseInt(rangeParts[1]) + 1
                            });
                        }
                    }
                }

                placesToReplace.sort(function(first, second) {
                    return second.from - first.from;
                });

                for (var iPlace = 0; iPlace < placesToReplace.length; iPlace++) {
                    var place = placesToReplace[iPlace];
                    message = message.substring(0, place.from) + "$emoticon#" + place.emote_id + "$" + message.substring(place.to);
                }

                return message.replace(/\$emoticon#(\d+)\$/g, function(code, emoteId) {
                    var url = 'http://static-cdn.jtvnw.net/emoticons/v1/' + emoteId + '/1.0';
                    return '<img class="smile" src="' + url +  '" />';
                });
            },
            replaceBttvEmoticons: function(message, emotes) {
                return message.replace(/(^| )?(\S+)?( |$)/g, function (code, b1, emote_key, b2) {
                    for(var emote in emotes) {
                        if(emotes[emote].emote_id == emote_key && emotes[emote].emote_url) {
                            return '<img class="btsmile" src="' + emotes[emote]['emote_url'] + '" />';
                        }
                    }
                    return code;
                });
            },
            replaceDefaultEmotions: function (message, emotes) {
                return message.replace(/:(\w+|\d+):/g, function(code, emote_key) {
                    for (var emote in emotes) {
                        if (!!emotes[emote] && emotes[emote]['emote_id'] == emote_key) {
                            return '<img class="smile" src="' + emotes[emote]['emote_url'] + '" />';
                        }
                    }

                    return code;
                });
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

                this.messages = this.messages.filter(function(message) {
                    var user = message.user.toLowerCase();
                    return usernames.indexOf(user) < 0;
                });
            },
            run: function (message) {
                if (!message.command)
                    return;

                switch (message.command) {
                    case 'reload':
                        window.location.reload();
                        break;
                    case 'remove_by_user':
                        this.removeByUsernames(message.user);
                        break;
                    case 'remove_by_id':
                        this.removeByIds(message.ids);
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
                        this.run(message);
                        break;
                    default:
                        message.time = new Date();
                        this.messages.push(message);
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
            }
        },
        filters: {}
    });
})(window.WebSocket, window.Vue, window.DOMPurify);