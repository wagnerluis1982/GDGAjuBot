#!/bin/bash

cd `dirname $0`

cd GDGAjuBot
git pull origin master
pip3 install -r requirements.txt
supervisorctl restart gdgajubot