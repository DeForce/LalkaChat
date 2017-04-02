#!/usr/bin/env bash
PORT=8080

curl -s -X POST -H 'Content-Type: application/json' -d '{"nickname":"HitboxTest","text":"hbTestMessage"}' http://localhost:${PORT}/rest/hitbox/push_message

sleep 1

curl -s http://localhost:${PORT}/rest/webchat/history | grep hbTestMessage
