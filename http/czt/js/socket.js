var MAX_MESSAGES = 70;
var find_location = window.location.href;
var RegExp = /:(\d+)/;
var find_list = RegExp.exec(find_location.toString());
var find_port = find_list[1];
var ws_url = "ws://127.0.0.1:".concat(find_port, "/ws");

// Chat settings
var timeout = 0;
var loadHistory = true;

var socket = new WebSocket(ws_url);

var chatMessages;
socket.onopen = function() {
    console.log("Socket connected")
    chatMessages = document.getElementById('ChatContainer');
};

socket.onclose = function(event) {
	if (event.wasClean) {
	    console.log("Socket closed cleanly")
	}
	else {
	    console.log("Socket closed not cleanly")
	}
};

socket.onmessage = function(event) {
	var incomingMessage = JSON.parse(event.data);
    if(incomingMessage.hasOwnProperty('command')) {
        runCommand(incomingMessage);
    }
    else {
        if (loadHistory) {
            showMessage(incomingMessage);
        }
        else if (!incomingMessage.hasOwnProperty('history')) {
            showMessage(incomingMessage);
        }
    }
};

socket.onerror = function(error) {
};

twitch_processEmoticons = function(message, emotes) {
	if (!emotes) {
		return message;
	}
	var placesToReplace = [];
	for (var emote in emotes) {
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
	placesToReplace.sort(function(first, second) {
		return second.from - first.from;
	});
	for (var iPlace = 0; iPlace < placesToReplace.length; ++iPlace) {
		var place = placesToReplace[iPlace];
		var emoticonRegex = message.substring(place.from, place.to);
		// var url = "http://static-cdn.jtvnw.net/emoticons/v1/" + place.emote_id + "/1.0"
		message = message.substring(0, place.from) + "$emoticon#" + place.emote_id + "$" +	message.substring(place.to);
	}

	return message;
};

htmlifyGGEmoticons = function(message, emotes) {
	return message.replace(/:(\w+|\d+):/g, function (code, emote_key) {
		for(var emote in emotes) {
			if(emote_key == emotes[emote]['emote_id']) {
				return "<img class='imgSmile' src=" + emotes[emote]['emote_url'] + ">";
			}
		}
		return code;
    });
};

htmlifyBTTVEmoticons = function(message, emotes) {
	return message.replace(/(^| )?(\S+)?( |$)/g, function (code, b1, emote_key, b2) {
		for(var emote in emotes) {
			if(emote_key == emotes[emote]['emote_id']) {
				return "<img class='imgSmile' src=" + emotes[emote]['emote_url'] + ">";
			}
		}
		return code;
    });
};

htmlifyTwitchEmoticons = function(message) {
    return message.replace(/\$emoticon#(\d+)\$/g, function (code, emoteId) {
		return "<img class='imgSmile' src='http://static-cdn.jtvnw.net/emoticons/v1/" + emoteId + "/1.0'>";
    });
};

escapeHtml = (function () {
    'use strict';
    var chr = { '"': '&quot;', '&': '&amp;', '<': '&lt;', '>': '&gt;' };
    return function (text) {
        return text.replace(/[\"&<>]/g, function (a) { return chr[a]; });
    };
}());

function removeMessage(element) {
    var elm = element || chatMessages.lastChild;
    chatMessages.removeChild(elm);
  }

function updateMessages() {
    if(chatMessages.children.length < MAX_MESSAGES) return;
    var element = chatMessages.lastChild;
    if(element.hasAttribute('timer-id')) {
        var timerId = element.getAttribute('timer-id');
        window.clearTimeout(timerId);
    }
    removeMessage(element);
  }


function showMessage(message) {
	var badge_colors = 1;

	var elements = {};
	elements['message'] = document.createElement('div');
	elements.message.setAttribute('class', 'msg');
	elements.message.setAttribute('id', message.id);
	elements.message.setAttribute('user', message.user);
	if(timeout > 0) {
		elements.message.setAttribute('timer-id', setTimeout(removeMessage, timeout * 1000, elements.message));
	}

	var messageJSON = message;

	if(messageJSON.hasOwnProperty('source')) {
		//console.log("message has source " + messageJSON.source);

		elements.message['source'] = document.createElement('div');
		elements.message.source.setAttribute('class', 'msgSource');

        elements.message.source['img'] = document.createElement('img');
        if(messageJSON.hasOwnProperty('source_icon')) {
            elements.message.source.img.setAttribute('src', messageJSON.source_icon);
        }
        else{
            elements.message.source.img.setAttribute('src', '/img/sources/' + messageJSON.source + '.png');
        }
        elements.message.source.img.setAttribute('class', 'imgSource');

		elements.message.source.appendChild(elements.message.source.img);
		elements.message.appendChild(elements.message.source);
	}

	if(messageJSON.hasOwnProperty('levels')) {
		elements.message['level'] = document.createElement('div');
		elements.message.level.setAttribute('class', 'msgLevel');

		elements.message.level['img'] = document.createElement('img');
		elements.message.level.img.setAttribute('class', 'imgLevel');
		elements.message.level.img.setAttribute('src', messageJSON.levels.url);

		elements.message.level.appendChild(elements.message.level.img);
		elements.message.appendChild(elements.message.level);
	}

	if(messageJSON.hasOwnProperty('s_levels')) {

		for (i = 0; i < messageJSON.s_levels.length; i++) {
			elements.message['s_level'] = document.createElement('div');
			elements.message.s_level.setAttribute('class', 'msgSLevel');

			elements.message.s_level['img'] = document.createElement('img');
			elements.message.s_level.img.setAttribute('class', 'imgSLevel');
			elements.message.s_level.img.setAttribute('src', messageJSON.s_levels[i].url);

			elements.message.s_level.appendChild(elements.message.s_level.img);
			elements.message.appendChild(elements.message.s_level);
		}
	}

	if(messageJSON.hasOwnProperty('badges')) {

		for (i = 0; i < messageJSON.badges.length; i++) {
			elements.message['badge'] = document.createElement('div');
			elements.message.badge.setAttribute('class', 'msgBadge');

			elements.message.badge['img'] = document.createElement('img');
			elements.message.badge.img.setAttribute('class', 'imgBadge');
			elements.message.badge.img.setAttribute('src', messageJSON.badges[i].url);

			if(badge_colors) {
				if(messageJSON.badges[i].badge == 'broadcaster') {
					elements.message.badge.img.setAttribute('style', 'background-color: #e71818');
				}
				else if(messageJSON.badges[i].badge == 'mod') {
					elements.message.badge.img.setAttribute('style', 'background-color: #34ae0a');
				}
				else if(messageJSON.badges[i].badge == 'turbo') {
					elements.message.badge.img.setAttribute('style', 'background-color: #6441a5');
				}
			}
			elements.message.badge.appendChild(elements.message.badge.img);
			elements.message.appendChild(elements.message.badge);
		}
	}

	if(messageJSON.hasOwnProperty('user')) {
		// console.log("message has user " + messageJSON.user);
		elements.message['user'] = document.createElement('div');
		elements.message.user.setAttribute('class', 'msgUser');
        var addString = messageJSON.user;

        if (messageJSON.hasOwnProperty('msg_type')) {
            if (messageJSON.msg_type == 'pubmsg') {
                addString += ": "
            }
        }
        else {
            addString += ": "
        }

		elements.message.user.appendChild(document.createTextNode(addString));

		elements.message.appendChild(elements.message.user);
	}

	if(messageJSON.hasOwnProperty('text')) {
		// console.log("message has text " + messageJSON.text);
		elements.message['text'] = document.createElement('div');
        if(messageJSON.source == 'sy') {
            elements.message.text.setAttribute('class', 'msgTextSystem');
        }
		else if(messageJSON.hasOwnProperty('pm') && messageJSON.pm == true) {
			elements.message.text.setAttribute('class', 'msgTextPriv');
		}
		else if(messageJSON.hasOwnProperty('mention') && messageJSON.mention == true){
			elements.message.text.setAttribute('class', 'msgTextMention');
		}
		else {
			elements.message.text.setAttribute('class', 'msgText');
		}

		if(messageJSON.source == 'tw') {
			messageJSON.text = htmlifyTwitchEmoticons(escapeHtml(twitch_processEmoticons(messageJSON.text, messageJSON.emotes)));
			if(messageJSON.hasOwnProperty('bttv_emotes')) {
				messageJSON.text = htmlifyBTTVEmoticons(messageJSON.text, messageJSON.bttv_emotes);
			}
		}
		else if(messageJSON.source == 'gg') {
			messageJSON.text = htmlifyGGEmoticons(messageJSON.text, messageJSON.emotes)
		}
		else if(messageJSON.source == 'fs') {
			messageJSON.text = htmlifyGGEmoticons(escapeHtml(messageJSON.text), messageJSON.emotes)
		}

		// elements.message.text.appendChild(document.createTextNode(messageJSON.text));
		elements.message.text.innerHTML = messageJSON.text;

		elements.message.appendChild(elements.message.text);

	}
	document.getElementById('ChatContainer').appendChild(elements.message);
    // updateMessages();
}

function runCommand(message) {
    if(message.command == 'reload'){
        window.location.reload();
    }
    else if(message.command == 'remove_msg') {
        if(message.ids) {
            message.ids.forEach(function(message_item) {
                item = document.getElementById(message_item)
                if (item) {
                    item.parentNode.removeChild(item)
                }
            })
        }
        else if(message.user) {
            message.user.forEach(function(user) {
                var children = chatMessages.childNodes
                var node_length = children.length - 1
                for(i=node_length; i >= 0; --i) {
                    if(children[i].getAttribute('user') == user) {
                        children[i].parentNode.removeChild(children[i])
                    }
                }
            })
        }
    }
    else {
        console.log("Got unknown command " + message.command)
    }
}

