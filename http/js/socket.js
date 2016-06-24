var socket = new WebSocket("ws://127.0.0.1:8080/ws");

socket.onopen = function() {
	console.log("Соединение установлено.");
};

socket.onclose = function(event) {
	if (event.wasClean) {
		console.log('Соединение закрыто чисто');
	} else {
		console.log('Обрыв соединения'); // например, "убит" процесс сервера
	}
	console.log('Код: ' + event.code + ' причина: ' + event.reason);
};

socket.onmessage = function(event) {
	var incomingMessage = event.data;
	showMessage(incomingMessage);
};

socket.onerror = function(error) {
	console.log("Ошибка " + error.message);
};

function showMessage(message) {
	var elements = {}
	elements['message'] = document.createElement('div');
	elements.message.setAttribute('class', 'msg')
	
	var messageJSON = JSON.parse(message);
  
	if(messageJSON.hasOwnProperty('source')) {
		//console.log("message has source " + messageJSON.source);
		
		elements.message['source'] = document.createElement('div');
		elements.message.source.setAttribute('class', 'msgSource');
		
		elements.message.source['img'] = document.createElement('img');
		elements.message.source.img.setAttribute('src', '/img/sources/' + messageJSON.source + '.png');
		
		elements.message.source.appendChild(elements.message.source.img);
		elements.message.appendChild(elements.message.source);
	}
	
	if(messageJSON.hasOwnProperty('user')) {
		// console.log("message has user " + messageJSON.user);
		elements.message['user'] = document.createElement('div');
		elements.message.user.setAttribute('class', 'msgUser');
		
		elements.message.user.appendChild(document.createTextNode(messageJSON.user + ": "));
		
		elements.message.appendChild(elements.message.user);
	}
	
	if(messageJSON.hasOwnProperty('text')) {
		// console.log("message has text " + messageJSON.text);
		elements.message['text'] = document.createElement('div');
		elements.message.text.setAttribute('class', 'msgText');
		
		elements.message.text.appendChild(document.createTextNode(messageJSON.text));
		
		elements.message.appendChild(elements.message.text);
	}
  
	document.getElementById('ChatContainer').appendChild(elements.message);
}