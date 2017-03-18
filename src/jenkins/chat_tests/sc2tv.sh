#!/usr/bin/env bash
PORT=8080

curl -s -X POST -H 'Content-Type: application/json' -d '{"nickname":"sc2tvTest","text":"sc2tvTestMessage"}' http://localhost:${PORT}/rest/sc2tv/push_message

sleep 1

curl -s http://localhost:${PORT}/rest/webchat/history | grep sc2tvTest
