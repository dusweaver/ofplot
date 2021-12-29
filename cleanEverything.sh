#!/bin/bash

find . -type f -name "Allclean" -exec sh -c '
    for Allclean do
        ( cd "${Allclean%/*}" && sh Allclean)
    done' sh {} +

rm -rf *.pkl
