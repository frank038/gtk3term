#!/bin/bash

thisdir=$(dirname "$0")
cd $thisdir

if [[ $# -eq 0 ]]; then
    python3 gtk3term.py
elif [[ $# -eq 2 ]]; then
    python3 gtk3term.py $1 "$2"
elif [[ $# -eq 4 ]]; then
    python3 gtk3term.py $1 "$2" $3 "$4"
fi

cd $HOME
