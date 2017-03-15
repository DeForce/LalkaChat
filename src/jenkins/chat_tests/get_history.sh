#!/usr/bin/env bash

echo "This is get_history test"
if [ -z $(curl localhost:8080/rest/webchat/history) ]; then
    exit 1
fi
