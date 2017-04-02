#!/usr/bin/env bash
nohup python main.py > chat.log 2>&1 &
ATTEMPTS=0

while [ ${ATTEMPTS} -lt 20 ]; do
    sleep 1
    ((ATTEMPTS++))
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

    if ! grep "BeamPro Testing mode online" chat.log; then
        continue
    fi

    if ! grep "Hitbox Testing mode online" chat.log; then
        continue
    fi

    sleep 5
    exit 0
done

echo "Chat didn't start successfully"
exit 1
