#!/bin/bash
while [ 1 ]
do 
	#Installing required package
	/usr/local/bin/pip install paho-mqtt
	echo "Starting MyStrom2HA"
    cp /mystrom2ha/mystrom2ha.py /data/mystrom2ha.py
    ln -s /mystrom2ha/login_icon.jpg /data/login_icon.jpg
    ln -s /mystrom2ha/mystrom2ha.css /data/mystrom2ha.css
	cd /data
	python mystrom2ha.py
	sleep 30
done
