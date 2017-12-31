#!/usr/bin/env bash
PORT=8080

curl -s -X POST -H 'Content-Type: application/json' -d '{"nickname":"twitchTest","text":"twitchTestMessage"}' http://localhost:${PORT}/rest/twitch/push_message

sleep 1

curl -s http://localhost:${PORT}/rest/webchat/history | grep twitchTest
