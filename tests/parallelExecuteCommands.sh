#!/bin/bash


parallel cp commands.sh ::: pitzDaily*/
parallel ::: pitzDaily*/commands.sh
