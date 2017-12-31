#!/usr/bin/env bash
nohup python main.py > chat.log 2>&1 &
ATTEMPTS=0

while [ ${ATTEMPTS} -lt 20 ]; do
    sleep 1
    ((ATTEMPTS++))
    if ! grep "LalkaChat loaded successfully" chat.log; then
        continue
    fi
    kill $(ps aux | grep main.py | grep -v grep | awk '{print $2}')
    sleep 5
    exit 0
done

echo "Chat didn't start successfully"
exit 1
