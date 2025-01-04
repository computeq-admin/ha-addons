#!/bin/bash
export MYSTROM2HA_ACCESS_PASSWORD=$(cat /data/options.json | python3 -c "import sys, json; print(json.load(sys.stdin)['Webservice_Password'])")
echo "Passwort set..."
while [ 1 ]
do 
	#Installing required package
	/usr/local/bin/pip install paho-mqtt
	echo "Starting MyStrom2HA"
	cp src/mystrom2ha.py /data/mystrom2ha.py
	cp -r resources /data/
	cd /data
 	pwd
	python mystrom2ha.py
	sleep 30
done
