#!/bin/bash

if [ -z "${VIRTUAL_ENV}" ]; then
    echo "activating poetry env at $(poetry env info --path)"
    source $(poetry env info --path)/bin/activate
fi
