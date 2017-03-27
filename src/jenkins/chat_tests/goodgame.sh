#!/usr/bin/env bash
PORT=8080

curl -s -X POST -H 'Content-Type: application/json' -d '{"nickname":"ggTest","text":"ggTestMessage"}' http://localhost:${PORT}/rest/goodgame/push_message

sleep 1

curl -s http://localhost:${PORT}/rest/webchat/history | grep ggTest
