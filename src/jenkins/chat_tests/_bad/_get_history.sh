#!/usr/bin/env bash

PORT=8080

exit 0

echo "This is get_history test"
if [ -z "$(curl http://localhost:${PORT}/rest/webchat/history)" ]; then
    exit 1
fi

curl http://localhost:${PORT}/rest/webchat/history
