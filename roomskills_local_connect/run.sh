#!/bin/bash
export RLC_IP=$(cat /data/options.json | python3 -c "import sys, json; print(json.load(sys.stdin)['home_assistant_ip'])")
echo "---------------------------------------------------"
echo "Roomskills Local Connect IP taken: $RLC_IP"
echo "---------------------------------------------------"
while [ 1 ]
do
        #Installing required package
        /usr/local/bin/pip install websocket-client
        /usr/local/bin/pip install roonapi
        /usr/local/bin/pip install paho-mqtt
        /usr/local/bin/pip install paramiko
        echo "Starting Roomskills Local Connect"
        if [ -f /data/config.json ]
        then
                echo "config found ..."
        else
                echo "no config, create empty config ..."
                echo '{"name": "Profil", "current_profile": "", "lang": "DE", "profiles": {}, "current_service": "", "service_states": {}}' > /data/config.json
        fi
        mkdir /opt/roomskills_local_connect
        cd /opt/roomskills_local_connect
        ln -s /data/config.json config.json
        echo "getting new Roomskills Local Connect version ..."
        /usr/bin/wget "https://www.roomskills.com/apps/get_rlc.php?os=python" -O roomskills_local_connect.py
        chmod +x roomskills_local_connect.py

        PIDRLC=`pidof roomskills_local_connect.py` > /dev/null
        JETZT=$(/bin/date +"%T")
        echo "$JETZT - Roomskills Local Connect is not running, starting ..."
        rm /opt/roomskills_local_connect/roomskills_local_connect.log /mnt/roomskills_local_connect.log
        touch /data/roomskills_local_connect.log
        ln -s /data/roomskills_local_connect.log /opt/roomskills_local_connect/roomskills_local_connect.log
        echo "Roomskills Local Connect IP: $RLC_IP"
        python roomskills_local_connect.py --service --docker
        sleep 30
done
