#!/usr/bin/env bash

mysql -e 'DROP DATABASE viewflow;'
mysql -e 'CREATE DATABASE viewflow DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;'
python3 ../manage.py migrate
python3 ../manage.py loaddata helloworld/fixtures/helloworld/default_data.json
python3 ../manage.py loaddata shipment/fixtures/shipment/default_data.json

python3 ../manage.py shell < data-population.py
