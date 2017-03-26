#!/usr/bin/env bash
set -x
if [ ! -d 'http/default_gui' ]; then
    cp -r http/default http/default_gui
fi
