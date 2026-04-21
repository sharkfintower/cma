#!/bin/bash
source startenv.sh
python ./makesite.py
source stopenv.sh
cd _site
../../scripts/deploy.sh
echo 'site deployed'
