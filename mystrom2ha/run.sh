#!/bin/bash
echo "------"
cat /data/options.json
echo "------"
export MYSTROM2HA_ACCESS_PASSWORD=$(cat /data/options.json | python3 -c "import sys, json; print(json.load(sys.stdin)['Webservice_Password'])")
while [ 1 ]
do 
	#Installing required package
	/usr/local/bin/pip install paho-mqtt
	echo "Starting MyStrom2HA"
	cp /mystrom2ha/mystrom2ha.py /data/mystrom2ha.py
	ln -s /mystrom2ha/resources /data/resources
	cd /data
	python mystrom2ha.py
	sleep 30
done
