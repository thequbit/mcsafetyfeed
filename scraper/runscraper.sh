#!/bin/sh

export WORKON_HOME=~/Envs
source /usr/local/bin/virtualenvwrapper.sh

workon mcsafetyfeed
python scraper.py
deactivate


