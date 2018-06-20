HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>Document</title>
</head>
<body>
    <script>
        (function() {
            'use strict';
 
            var host = 'localhost:{{ port }}';
 
            var interval = 1 * 1000;
            var wsUrl = 'ws://' + host + '/ws';
            var appUrl = 'http://' + host + '';
 
            function RWebSocket() {}
 
            RWebSocket.prototype.navigate = function() {
                window.location.replace(appUrl);
            }
 
            RWebSocket.prototype.wait = function() {
                setTimeout(this.navigate.bind(this), 2000);
            }
 
            RWebSocket.prototype.reconnect = function(event) {
                setTimeout(this.open.bind(this), interval);
            }
 
            RWebSocket.prototype.open = function() {
                this.instance = new WebSocket(wsUrl);
                this.instance.onclose = this.reconnect.bind(this);
                this.instance.onopen = this.wait.bind(this);
            }
 
            new RWebSocket().open();
        })();
    </script>
</body>
</html>
"""