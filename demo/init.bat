mysql -e 'DROP DATABASE viewflow;'
mysql -e 'CREATE DATABASE viewflow DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;'

python ..\manage.py migrate
python ..\manage.py loaddata helloworld\fixtures\helloworld\default_data.json
python ..\manage.py loaddata shipment\fixtures\shipment\default_data.json
python ..\manage.py loaddata orderit\fixtures\orderit\default_data.json

python ..\manage.py shell < data-population.py

python ..\manage.py compilemessages -l zh_Hans
