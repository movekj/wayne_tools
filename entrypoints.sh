#!/bin/bash

set -e

if [[ "$#" -eq 0 ]]
then
    echo 'hello world'
else
    exec "$@"
fi
