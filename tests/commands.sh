#!/bin/bash
cd ${0%/*} || exit 1


rm commands.sh
blockMesh
simpleFoam
postProcess -func sampleAxial
postProcess -func sampleRadial
