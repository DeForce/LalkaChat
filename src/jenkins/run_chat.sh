#!/usr/bin/env bash
nohup python main.py > chat.log 2>&1 &

while true; do
    sleep 1
    if ! grep "LalkaChat loaded successfully" chat.log; then
        continue
    fi

    if ! grep "GG Testing mode online" chat.log; then
        continue
    fi

    if ! grep "sc2tv Testing mode online" chat.log; then
        continue
    fi

    if ! grep "twitch Testing mode online" chat.log; then
        continue
    fi
    break
done

sleep 5
