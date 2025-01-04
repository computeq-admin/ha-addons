#!/usr/local/bin/python3
#   File : mystrom2ha.py
#   Author: ingo.keutgen@computeq.co
#   Date: 18.03.2024
#   Description : Tool to programm mystrom buttons and PIRs in order to forward activities to Homeassistant
#   Code ownership : This code is owned by ComputeQ UG, Pelm Germany
#                    If you want to use or reuse the code or part of it
#                    please contact dev@computeq.co
#
# create multiarch docker
# cd home/dev/dev/mystrom2ha/src
# sudo docker buildx build --push --platform linux/386,linux/amd64,linux/arm/v5,linux/arm/v7,linux/arm64/v8 --tag computequg/mystrom2ha:latest .

import os
import threading
import logging
import sys
import json
import locale
import time
import datetime
from http.server import BaseHTTPRequestHandler, HTTPStatus, HTTPServer
import socket
from socket import getaddrinfo, AF_INET, gethostname
import urllib
import urllib.request
import urllib.parse
from urllib.parse import urlparse

import paho.mqtt.client as mqtt_client
import paho.mqtt.publish as mqtt_publish
import paho.mqtt.subscribe as mqtt_subscribe

#global variables
my_local_ip = ""
button_request_port = 32570
end_ha2mqtt = False
my_lang = "DE"
my_config = dict()
lang = dict()
access_password = ""
button_search_running = False
button_ips = []
the_found_button_type = {}
the_found_button_mac = {}
given_password = ""
the_percentage = ""
timeout_start = time.time() - 600


def get_local_ip():
    try:
        if ('MYSTROM2HA_IP' in os.environ):
            the_ip = os.environ.get('MYSTROM2HA_IP')
        else:
            the_ip = ''

    except Exception:
        the_ip = ''

    if (the_ip == ''):
        my_ips = list()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            the_ip = s.getsockname()[0]
        except Exception:
            the_ip = ''
        finally:
            s.close()

        if len(the_ip) < 1:
            for ip in getaddrinfo(host='localhost', port=None, family=AF_INET):   
                if ip[4][0] not in my_ips and "127.0" not in ip[4][0]:
                    my_ips.append(ip[4][0])
                    logging.info("new IP: " + ip[4][0])
            if len(my_ips) < 1:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.connect(('<broadcast>', 0))
                my_ips.append(str(s.getsockname()[0]))

            the_ip = my_ips[0]   

    return the_ip

def get_script_directory():
    path = os.path.realpath(sys.argv[0])
    if os.path.isdir(path):
        return path
    else:
        return os.path.dirname(path)

def write_sub_head_line (the_instance, the_title):
    the_instance.wfile.write(bytes("<br><p style=\"margin-left: 15px; font-size:22px;\">" + the_title + "</p>", "utf-8"))

def write_input_text (the_instance, the_id, the_name, the_label, the_value, the_required):
    the_instance.wfile.write(bytes("<div class=\"rs-input-group\">", "utf-8"))
    the_instance.wfile.write(bytes("<input type=\"text\" id=\"" + the_id + "\" name=\"" + the_name + "\" class=\"rs-input\" value=\"" + the_value + "\"", "utf-8"))
    if the_required:
        the_instance.wfile.write(bytes(" required=\"\"", "utf-8"))
    the_instance.wfile.write(bytes(">", "utf-8"))
    the_instance.wfile.write(bytes("<span class=\"rs-highlight\"></span><span class=\"rs-bar\"></span>", "utf-8"))
    the_instance.wfile.write(bytes("<label for=\"" + the_id + "\" class=\"rs-input-label\">" + the_label + "</label>", "utf-8"))
    the_instance.wfile.write(bytes("</div>", "utf-8"))

def test_mqtt():
    global my_config
    the_return = False
    try:
        the_toplevel_topic = my_config["mqtt_base_topic"]
        the_topic = the_toplevel_topic +"/"
        try:
            the_mqtt_client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2,"mystrom2ha_client_"+my_config["mystrom2ha_ip"])
        except:
            the_mqtt_client = mqtt_client.Client("mystrom2ha_client_"+my_config["mystrom2ha_ip"])
        if my_config["mqtt_user"] != "":
            the_mqtt_client.username_pw_set(my_config["mqtt_user"], my_config["mqtt_password"])
        the_mqtt_client.connect(my_config["mqtt_ip"], port=int(my_config["mqtt_port"]), keepalive=60, bind_address="")
        the_mqtt_client.loop_start()
        the_mqtt_client.publish(the_topic+"/action","Test-connection from "+my_config["mystrom2ha_ip"])
        time.sleep (1)
        the_return = the_mqtt_client.is_connected()
        the_mqtt_client.loop_stop()
        the_mqtt_client.disconnect()
    except Exception as ex:
        the_return = False
        logging.error("error test_mqtt - "+str(ex))

    return the_return

def read_config():
    global my_config
    if os.path.isfile(get_script_directory() + '/config.json'):
        with open(get_script_directory() + '/config.json', 'r') as f:
            my_config = json.load(f)
    else:
        default_locale = locale.getlocale()[0]
        if default_locale.startswith( 'de'):
            my_lang = "DE"
        else:
            my_lang = "EN"
        my_config["lang"] = my_lang
        my_config["mystrom2ha_ip"] = get_local_ip()
        my_config["mqtt_ip"] = my_config["mystrom2ha_ip"]
        my_config["mqtt_port"] = "1883"
        my_config["mqtt_ha_topic"] = "homeassistant"
        my_config["mqtt_base_topic"] = "mystrom2ha"
        my_config["mqtt_user"] = ""
        my_config["mqtt_password"] = ""

def write_config ():
    global my_config
    global my_lang
    with open(get_script_directory() +'/config.json', 'w') as f:
        my_config["lang"] = my_lang
        json.dump(my_config, f)    

def declare_text_snippets_de():
    global lang
    global my_local_ip
    global button_request_port
    lang['lang'] = "DE"
    lang['hello'] = "Hallo"
    lang['back'] = "Zurück"
    lang['cancel'] = "Abbrechen"
    lang['close'] = "Schließen"
    lang["retry"] = "Erneut versuchen"
    lang['or'] = "oder"
    lang['continue'] = "weiter"
    lang['login_language_change'] = "<a href=\"/webif?lang=EN\">To the login in English</a>"
    lang['service_connection'] = "Service Einstellungen"
    lang['messages'] = "Nachricht(en)"
    lang['button_config'] = "myStrom Button Konfiguration"
    lang['search_buttons'] = "myStrom Buttons suchen"
    lang['add_button'] = "myStrom Button hinzufügen"
    lang["search_finished"] = "Die Suche ist erfolgreich abgeschlossen."
    lang['button_ip'] = "IP des myStrom Buttons"
    lang['program_button'] = "Button programmieren"
    lang['button_manual_ip'] = "Manuelle Eingabe der IP Adresse"
    lang["programm_button_hint_1"] = "<UL><li>Zuerst sollte der myStrom Button in den Werkszustand gesetzt werden. Bei einem myStrom Button Gen1 erfolgt dies mittels langem Druck auf den Button und wenn die Farbe des Buttons sich ändert dan den Button erneut drücken.</li><li>Danach Verbindet man den Button mit Hilfe des 'myStrom Button Trouble Shooting Tool (verfügbar für Windows und macOS) mit dem WLAN Netzwerk. Dann sollte der Button nach einer kurzen Zeit im Konfigurationsmodus und bereit für die Programmierung sein.</li><li>myStrom Button+: Beim myStrom Button+ öffnet man die Rückseite durch Drehen des Deckels im Uhrzeigersinn, dann entfernt man kurz die Batterien und setzt sie wieder ein. Der Button sollte jetzt für eine gewisse Zeit im Konfigurationsmodus und bereit für die Programmierung sein.</li><li>Nun betätigen wir den Button'"+lang['search_buttons']+"' um die Suche nach dem Button zu starten. Achtung: Die Suche kann etwas dauern!</li><li>Falls MyStrom2HA sich nicht im lokalen Netz befindet (Network nicht im 'Host' Modus) kann man den Button auch gleich durch Angabe der IP Adresse und einen Klick auf Button '"+lang['program_button']+"' anbinden.</li></ul>"
    lang["no_button_found"] = "Kein Button gefunden. Anscheinend war der Button nicht mit Deinem Netzwerk verbunden bzw. nicht im Programmiermodus. Bitte prüfe nochmals die kleine Anleitung und versuche es erneut."  
    lang["search_running"] = "Da ist etwas schief gelaufen - es läuft noch eine Suche. Bitte klicke auf den folgenden Button, sobald die Suche 100% erreicht hat."
    lang['select_button'] = "Wähle den Button"
    lang["button_programming_ok"] = "Buttonprogrammierung - OK. Der Button konnte erfolgreich programmiert werden:"
    lang["button_programming_nok"] = "Buttonprogrammierung nicht OK. Anscheinend war der Button nicht mit Deinem Netzwerk verbunden bzw. nicht im Programmiermodus. Bitte prüfe nochmals die kleine Anleitung und versuche es erneut."
    lang["button_search_title"] = "Buttonsuche"
    lang["button_search"] = "Suche Buttons ..."
    lang["button_found_1"] = "Button "
    lang["button_found_2"] = " gefunden."
    lang['headline'] = "MyStrom2HA"
    lang['info_1'] = "MyStrom2HA wurde erfolgreich installiert."
    lang['info_2'] = "Bitte vervollständigen sie die unteren Parameter um die Einrichtung abzuschließen."
    lang['login'] = "Anmeldung"
    lang['login_text'] = "Bitte geben Sie das Passwort ein..."
    lang['do_login'] = "Anmelden"
    lang['password'] = "Passwort"
    lang['login_failed'] = "<font color=\"red\">Falsches Passwort!</font>"
    lang['config_mystron2ha'] = "MyStrom2HA Konfigurieren"
    lang['update'] = "Aktualisieren"
    lang["mqtt_ip"] = "MQTT Server IP"
    lang["mqtt_port"] = "MQTT Server Port"
    lang["mqtt_base_topic"] = "Top-Level MQTT Topic"
    lang["mqtt_ha_topic"] = "Homeassistant Discovery Topic"
    lang["mqtt_user"] = "MQTT User"
    lang["mqtt_password"] = "MQTT Passwort"
    lang["mystrom2ha_ip"] = "MyStrom2HA IP"
    lang["button_ip"] = "Button IP"
    lang["mqtt_connection_ok"] = "OK - die Verbindung zum MQTT Server konnte hergestellt werden."
    lang["mqtt_connection_nok"] = "Error - die Verbindung zum MQTT Server konnte noch nicht hergestellt werden. Überprüfen sie die Daten und versuchen sie es erneut."

def declare_text_snippets_en():
    global lang
    global my_local_ip
    global button_request_port
    lang['lang'] = "EN"
    lang['hello'] = "Hello"
    lang['back'] = "Back"
    lang['cancel'] = "Cancel"
    lang['close'] = "Close"
    lang["retry"] = "Retry"
    lang['or'] = "or"
    lang['continue'] = "continue"
    lang['login_language_change'] = "<a href=\"/webif?lang=DE\">Zum Login in Deutsch</a>"
    lang['service_connection'] = "Service setup"
    lang['messages'] = "Message(s)"
    lang['button_config'] = "myStrom button configuration"
    lang['search_buttons'] = "search myStrom Buttons"
    lang['add_button'] = "add myStrom Button"
    lang["search_finished"] = "The search was successfull."
    lang['button_ip'] = "IP of myStrom button"
    lang['program_button'] = "Program the button"
    lang['button_manual_ip'] = "Manual input of the IP address"
    lang["programm_button_hint_1"] = "<ul><li>myStrom button: First the myStrom button should be set to factory defaults and then be connected to the Wifi network using the myStrom trouble shooting tool. The myStrom trouble shooting tool is available for Windows and macOS.</li><li>myStrom Button+: Open the myStrom Button+ by rotating the cover on the back clockwise, then remove the batteries and enter them again. Then the button should enter the configuration mode for some time.</li><li>Now we click on the button '"+lang['search_buttons']+"' to find the button. Remark: The search can take up to 1 minute time!</li><li>If MyStrom2HA is not directly connected to the local network (Network mode is not 'Host'), you can enter the button ip directly in the field below and programm the button directly by clicking on '"+lang['program_button']+"'.</li></ul>"
    lang["no_button_found"] = "No buttons found. Unfortunately it seems the button was either not connected to the local network or it was set to the programming mode yet. Please check the short setup manual and try again."  
    lang["search_running"] = "Something went wrong, there is still a search running - please click on the following button once the counter has reached 100%."
    lang['select_button'] = "Select the button"
    lang["button_programming_ok"] = "Programming of the button - OK :"
    lang["button_programming_nok"] = "Programming of the button not OK. Unfortunately it seems the button was either not connected to the local network or it was set to the programming mode yet. Please check the short setup manual and try again."
    lang["button_search_title"] = "Button search"
    lang["button_search"] = "searching buttons ..."
    lang["button_found_1"] = "button "
    lang["button_found_2"] = " found."
    lang['headline'] = "MyStrom2HA"
    lang['info_1'] = "MyStrom2HA has been installed successfully."
    lang['info_2'] = "Please fill out the configuration below if necessary."
    lang['login'] = "Login"
    lang['login_text'] = "Please enter the password..."
    lang['do_login'] = "login"
    lang['password'] = "Password"
    lang['login_failed'] = "<font color=\"red\">Wrong Password!</font>"
    lang['config_mystron2ha'] = "Configure MyStrom2HA"
    lang['update'] = "Update"
    lang["mqtt_ip"] = "MQTT Server IP"
    lang["mqtt_port"] = "MQTT Server Port"
    lang["mqtt_base_topic"] = "Top-Level MQTT Topic"
    lang["mqtt_ha_topic"] = "Homeassistant Discovery Topic"
    lang["mqtt_user"] = "MQTT User"
    lang["mqtt_password"] = "MQTT Password"
    lang["mystrom2ha_ip"] = "MyStrom2HA IP"
    lang["button_ip"] = "Button IP"
    lang["mqtt_connection_ok"] = "OK - the connection to the MQTT Server could be established."
    lang["mqtt_connection_nok"] = "Error - the connection to the MQTT Server could not be established. Please check the values and try again."

def programm_mystrom_button (button_selected_ip):
    global my_config
    global button_request_port
    the_target_ip = my_config["mystrom2ha_ip"]
    the_target_port = button_request_port
    the_result = "nok"
    button_success = False
    try:
        #get mac and type
        url = "http://"+ button_selected_ip + "/api/v1/info"
        print("url:"+url)
        request = urllib.request.Request(url)
        response = urllib.request.urlopen(request, timeout=2)
        the_response_json = response.read().decode("utf8")
        the_response = json.loads(the_response_json)
        the_type_number = the_response['type']
        if the_type_number == 103:
            the_button_type = "myStrom Button Plus Gen1"
        elif the_type_number == 104:
            the_button_type = "myStrom Button"
        elif the_type_number == 110:
            the_button_type = "myStrom Motion Sensor"
        elif the_type_number == 118:
            the_button_type = "myStrom Button Plus Gen2"
        else:
            the_button_type = "unknown"
        the_mac_id = the_response['mac']
        # get Battery Level
        if the_type_number == 103 or the_type_number == 104:
            url = "http://"+ button_selected_ip + "/api/v1/device"
            request = urllib.request.Request(url)
            response = urllib.request.urlopen(request, timeout=2)
            the_response_json = response.read().decode("utf8")
            the_response = json.loads(the_response_json)
            the_voltage = the_response[the_mac_id]['voltage']
        elif the_type_number == 118:
            url = "http://"+ button_selected_ip + "/api/v1/sensors"
            request = urllib.request.Request(url)
            response = urllib.request.urlopen(request, timeout=2)
            the_response_json = response.read().decode("utf8")
            the_response = json.loads(the_response_json)
            the_voltage = the_response['battery']['voltage']
        elif the_type_number == 110:
            the_voltage = 5.0
        if the_voltage > 4.0:
            the_battery = "100"
        elif the_voltage < 3.0:
            the_battery = "0"
        else:
            the_battery = str (  round(  (the_voltage - 3.0) * 100 / ( 4.0 - 3.0)  )  )

        if the_type_number == 103 or the_type_number == 104:
            url = "http://"+ button_selected_ip + "/api/v1/action/generic"
            data = "get://"+the_target_ip+":"+str(the_target_port)+"/button_report"
            response = urllib.request.urlopen(url, data = data.encode('ascii'), timeout=5)
            print ("program_response:"+response.read().decode("utf8") )
        elif the_type_number == 118:
            url = "http://"+ button_selected_ip + "/api/v1/action/generic/generic"
            data = "get://"+the_target_ip+":"+str(the_target_port)+"/button_report"
            response = urllib.request.urlopen(url, data = data.encode('ascii'), timeout=5)
            print ("program_response:"+response.read().decode("utf8") )
        elif the_type_number == 110:
            #allow motion sensors to be programmed
            url = "http://"+ button_selected_ip + "/api/v1/action/pir/generic"
            data = "get://"+the_target_ip+":"+str(the_target_port)+"/button_report"
            response = urllib.request.urlopen(url, data = data.encode('ascii'), timeout=5)
            print ("program_response:"+response.read().decode("utf8") )
        
        button_success = True

    except Exception as ex:
        logging.error("error programming button:"+ str(ex))
        button_success = False

    if button_success :
        the_result = "ok"
    else:
        the_result = "nok"

    return the_result


def set_button_ips(the_instance):
    global the_percentage
    global button_ips
    global my_local_ip
    global the_found_button_type
    global the_found_button_mac
    button_ips = []
    test_ok = False
    tmp = my_local_ip.split(".")
    the_ip_range = my_local_ip[:len(my_local_ip)-len(tmp[-1])]
    the_percentage = "10%";

    #print("Erwarte Broadcast ...")
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) # UDP
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    # Enable broadcasting mode
    client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    client.bind(("", 7979))
    client.settimeout(4)
    the_found_button_type = {}
    the_found_button_mac = {}
    t_end = time.time() + 9
    while time.time() < t_end:
        the_percentage = "50%"
        try:
            data, addr = client.recvfrom(8)
            ip = addr[0]
            the_type = data[6]
            the_mac = hex(data[0])[2:]+hex(data[1])[2:]+hex(data[2])[2:]+hex(data[3])[2:]+hex(data[4])[2:]+hex(data[5])[2:]
            # 102	Bulb
            # 103	Button plus 1st generation
            # 104	Button small/simple
            # 105	LED Strip
            # 106	Switch CH
            # 107	Switch EU
            # 110	Motion Sensor
            # 112	Gateway
            # 113	STECCO/CUBO
            # 118	Button Plus 2nd generation
            # 120	Switch Zero
            if ( (the_type == 103) or (the_type == 104) or (the_type == 118) or (the_type == 110) ):
                the_found_button_type[ip] = str(the_type)
                the_found_button_mac[ip] = the_mac
            else:
                pass
        except:
            pass
    the_percentage = "90%";
    for the_test_ip in list(the_found_button_type.keys()):
        button_ips.append(the_test_ip)
        the_mac_id = the_found_button_mac[the_test_ip]
        if the_found_button_type[the_test_ip] == "103" :
            the_button_type = "myStrom Button Plus Gen1"
        if the_found_button_type[the_test_ip] == "104" :
            the_button_type = "myStrom Button"
        elif the_found_button_type[the_test_ip] == "118" :
            the_button_type = "myStrom Button Plus Gen2"
        else:
            the_button_type = "unknown"

        the_instance.wfile.write(bytes("</p><p style=\"margin-left: 15px; font-size:22px;\">"+lang["button_found_1"]+" "+the_button_type+" "+the_mac_id[-6:]+lang["button_found_2"]+" ("+the_test_ip+")</p><p style=\"margin-left: 15px; font-size:22px;\">", "utf-8"))
    the_percentage = "100%";

def write_web_top_page (the_instance, the_url):
    global my_lang
    global given_password
    the_instance.wfile.write(bytes("<html><head><title>" + lang['headline'] + "</title>", "utf-8"))
    the_instance.wfile.write(bytes("<meta charset=\"UTF-8\">", "utf-8"))
    the_instance.wfile.write(bytes("<link rel=\"stylesheet\" href=\"/mystrom2ha.css\">", "utf-8"))
    the_instance.wfile.write(bytes("<link href=\"https://fonts.googleapis.com/icon?family=Material+Icons\" rel=\"stylesheet\">", "utf-8"))
    the_instance.wfile.write(bytes("<script src=\"https://ajax.googleapis.com/ajax/libs/jquery/3.7.1/jquery.min.js\"></script>", "utf-8"))
    the_instance.wfile.write(bytes("</head>", "utf-8"))
    the_instance.wfile.write(bytes("<body>", "utf-8"))
    the_instance.wfile.write(bytes("<div id=\"top_bar\" class=\"navbar navbar-default\"><table width=\"100%\" border=\"0\"> <tbody><tr><td align=\"left\" valign=\"bottom\" style=\"padding: 15px 14px 0px 15px;\"><a href='/webif?password="+urllib.parse.quote(given_password)+"' style=\"color:white; font-size:28px; text-decoration: none; \"><i class=\"material-icons\">home</i> " + lang['headline'] + "</a><p></p></td><td align=\"right\" width=\"80pt\" style=\"padding-left:5px; padding-top:10px;\">", "utf-8"))
    if my_lang == "DE":
        the_instance.wfile.write(bytes("<a href=\""+ the_url+ "&lang=EN\" class=\"navbar-nav-icon\"><i class=\"material-icons\">language</i></a>", "utf-8"))
    else:
        the_instance.wfile.write(bytes("<a href=\""+ the_url+ "&lang=DE\" class=\"navbar-nav-icon\"><i class=\"material-icons\">language</i></a>", "utf-8"))
    the_instance.wfile.write(bytes("&nbsp;<a href=\"/logout\" class=\"navbar-nav-icon\"><i class=\"material-icons\">logout</i></a>", "utf-8"))
    the_instance.wfile.write(bytes("</td></tr></tbody></table></div>", "utf-8"))


def write_web_footer_page (the_instance):
    the_instance.wfile.write(bytes("<div id =\"rsFooter\" class =\"footer\" style=\"height:22;\">", "utf-8"))
    the_instance.wfile.write(bytes("<p class=\"footertext\">(c) <a href = \"https://www.computeq.co/\" class=\"footerlink\">MyStrom2HA by Computeq</a> 2024-" + str(datetime.date.today().year) + "</p>", "utf-8"))
    the_instance.wfile.write(bytes("</div>", "utf-8"))
    the_instance.wfile.write(bytes("</body></html>", "utf-8"))

def write_remark (the_instance, the_remark):
    the_instance.wfile.write(bytes("<br><p style=\"margin-left: 15px; font-size:18px;\">" + the_remark + "</p>", "utf-8"))

def write_hint (the_instance, the_summary, the_details):
    the_instance.wfile.write(bytes("<details><summary>"+the_summary+"</summary>" + the_details + "</details>", "utf-8"))

class button_thread(threading.Thread):
    def __init__(self, i):
        threading.Thread.__init__(self)
        self.i = i
        self.daemon = True
        self.start()
    def run(self):
        global button_ips
        global end_ha2mqtt
        httpd = HTTPServer(addr, button_server_handler, False)

        # Prevent the HTTP server from re-binding every handler.
        httpd.socket = sock
        httpd.server_bind = self.server_close = lambda self: None

        while not end_ha2mqtt:
            httpd.handle_request()
        httpd.server_close()
        logging.info("server stopped.")  

class button_server_handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        try:
            logging.info("%s - - %s\n" % (self.address_string(),format%args))
        except:
            logging.info("%s - - %s\n" % (self.address_string(),format%args))

    def do_HEAD(self):
        for the_header in self.headers:
            logging.info("header:"+str(the_header))
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()


    def do_GET(self):
        global my_lang
        global end_ha2mqtt
        global access_password
        global button_search_running
        global button_ips 
        global the_found_button_type
        global the_found_button_mac
        global given_password
        global timeout_start
        global my_config
        global search_given_password
        is_mobile = 'false'
        the_message = ""
        query_components = dict()
        wrong_password = False
        # Send apropriate header
        if self.path.endswith('.jpg') or self.path.endswith('.jpeg') :
            self.send_response(200)
            self.send_header("Content-type", "image/jpeg")
            self.end_headers()
        elif self.path.endswith('.png'):
            self.send_response(200)
            self.send_header("Content-type", "image/png")
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
        # request content
        if ("=" in self.path):
            query = urlparse(self.path).query
            query_components = dict(qc.split("=") for qc in query.split("&"))
        if "lang" in query_components.keys():
            my_lang = query_components["lang"]
        if "password" in query_components.keys():
            given_password = urllib.parse.unquote(query_components["password"])
            timeout_start = time.time()
        elif (time.time() - timeout_start > 600):
            given_password = ""
        if "password" in query_components.keys() and given_password != access_password:
            wrong_password = True
        if self.path == '/logout' or self.path == '/' or self.path == '' :
            given_password = ""
        if my_lang == "DE":
            declare_text_snippets_de()
        else:
            declare_text_snippets_en()
        if self.path.endswith('.css') or self.path.endswith('.htm') or self.path.endswith('.html') :
            if os.path.isfile(get_script_directory() + self.path):
                with open(get_script_directory() + self.path, 'r') as f:
                    self.wfile.write(bytes(f.read(), "utf-8"))
        elif self.path.endswith('.jpg') or self.path.endswith('.jpeg') :
            if os.path.isfile(get_script_directory() + self.path):
                with open(get_script_directory() + self.path, 'rb') as f:
                    the_image_in_bytes = f.read()
                    self.wfile.write(the_image_in_bytes)

        elif self.path.startswith( '/webif' ) and given_password == access_password:
            write_web_top_page (self, "/webif?password="+urllib.parse.quote(given_password) )
            if "action" in query_components.keys() :
                if query_components["action"] == "program_button_execute":
                    if "button_ip" in query_components.keys():
                        the_ip = query_components["button_ip"]
                        write_sub_head_line (self, lang["program_button"]+" - "+the_ip)
                        the_programming_status = programm_mystrom_button (the_ip)

                        if the_programming_status == "ok" :
                            write_sub_head_line (self, lang["button_programming_ok"])
                        else:
                            write_hint (self, lang["search_buttons"], lang["programm_button_hint_1"])
                            write_sub_head_line (self, lang["button_programming_nok"])

                    else:
                        write_sub_head_line (self,"ERROR")
                    
                    self.wfile.write(bytes("<center><a href='/webif?password=" + urllib.parse.quote(given_password) +"' class='btn btn-primary'>" + lang['close'] + "</a></center>", "utf-8"))
                    
                elif query_components["action"] == "program_button_start":
                    write_sub_head_line (self, lang["program_button"])
                    self.wfile.write(bytes("<table width='100%' border='0' >", "utf-8"))

                    for the_number in button_ips:
                        the_mac_id = the_found_button_mac[the_number]
                        the_type = the_found_button_type[the_number]
                        the_button_type = ""
                        if the_type == "103":
                            the_button_type = "myStrom Button Plus Gen1"
                        elif the_type == "104":
                            the_button_type = "myStrom Button"
                        elif the_type == "110":
                            the_button_type = "myStrom Motion Sensor"
                        elif the_type == "118":
                            the_button_type = "myStrom Button Plus Gen2"
                        else:
                            the_button_type = "unknown"

                        self.wfile.write(bytes("<tr>", "utf-8"))
                        self.wfile.write(bytes("<form id=\""+the_mac_id+"_form\" action=\"webif\" method=\"get\">", "utf-8"))
                        self.wfile.write(bytes("<td width='20px'></td>", "utf-8"))
                        self.wfile.write(bytes("<td align='right'><font size = '+2'>"+the_button_type+" "+the_number+"</font> ("+the_mac_id+")</td>", "utf-8"))
                        self.wfile.write(bytes("<td align='left'>&nbsp;", "utf-8"))
                        self.wfile.write(bytes("<input type=\"hidden\" id='password' name='password' class='btn btn-primary' value=\"" + urllib.parse.quote(given_password) + "\" />", "utf-8"))
                        self.wfile.write(bytes("<input type=\"hidden\" id='action' name='action' class='btn btn-primary' value=\"program_button_execute\" />", "utf-8"))
                        self.wfile.write(bytes("<input type=\"hidden\" id='button_ip' name='button_ip' class='btn btn-primary' value=\"" + urllib.parse.quote(the_number) + "\" />", "utf-8"))
                        self.wfile.write(bytes("<input type=\"submit\" class='btn btn-primary' value=\"" + lang['program_button'] + "\" />", "utf-8"))
                        self.wfile.write(bytes("</td>", "utf-8"))

                        self.wfile.write(bytes("<td width='20px'></td>", "utf-8"))
                        self.wfile.write(bytes("</form></tr>", "utf-8"))
                    self.wfile.write(bytes("</table>", "utf-8"))

                elif query_components["action"] == "search_button":
                    search_given_password = given_password
                    self.wfile.write(bytes("", "utf-8"))
                    self.wfile.write(bytes("<script>function start_search() { ", "utf-8"))
                    self.wfile.write(bytes("document.getElementById('the_state_div').innerHTML = ''; ", "utf-8"))
                    self.wfile.write(bytes("document.getElementById('the_percentage').innerHTML = '1%'; ", "utf-8"))
                    self.wfile.write(bytes("document.getElementById('the_search_div').innerHTML = ''; ", "utf-8"))
                    self.wfile.write(bytes("var $link = '/start_button_search' ; ", "utf-8"))
                    self.wfile.write(bytes("$( '#the_search_div' ).load( $link );}", "utf-8"))
                    self.wfile.write(bytes("function set_state() { ", "utf-8"))
                    self.wfile.write(bytes("var $link2 = '/button_search_state' ; ", "utf-8"))
                    self.wfile.write(bytes("$( '#the_percentage' ).load( $link2 );}", "utf-8"))
                    self.wfile.write(bytes("function update_state() { ", "utf-8"))
                    self.wfile.write(bytes("setInterval(function(){ set_state(); }, 2000); }", "utf-8"))
                    self.wfile.write(bytes("</script>", "utf-8"))

                    write_hint (self, lang["search_buttons"], lang["programm_button_hint_1"])

                    self.wfile.write(bytes("<div id='the_state_div'></div><center><div id='the_percentage'></div></center>", "utf-8"))

                    self.wfile.write(bytes("<div id='the_search_div'>", "utf-8"))

                    self.wfile.write(bytes("<center><button class='btn btn-primary' onclick=\"start_search(); update_state(); \">"+lang['button_search']+"</button></center>", "utf-8"))

                    self.wfile.write(bytes("<p></p><form id=\"program_button_ip_form\" action=\"webif\" method=\"get\">", "utf-8"))
                    self.wfile.write(bytes("<input type=\"hidden\" id= \"action\" name= \"action\" value=\"program_button_execute\">", "utf-8"))
                    self.wfile.write(bytes("<input type=\"hidden\" id= \"password\" name= \"password\" value=\""+urllib.parse.quote(given_password)+"\">", "utf-8"))
                    self.wfile.write(bytes("<div style=\"margin-left:50px; margin-right:50px ; width:100%;\"><table><tr><td>", "utf-8"))
                    write_input_text (self, "button_ip", "button_ip", lang["button_ip"], "", True)
                    self.wfile.write(bytes("</td><td><center><input type=\"submit\" class='btn btn-primary' value=\"" + lang['program_button'] + "\" /></center>", "utf-8"))
                    self.wfile.write(bytes("</td></tr></table></div></form>", "utf-8"))


                    self.wfile.write(bytes("</div>", "utf-8"))

                elif query_components["action"] == "m2h_config":
                    if "mystrom2ha_ip" in query_components.keys():
                        my_config["mystrom2ha_ip"] = urllib.parse.unquote(query_components["mystrom2ha_ip"])
                    if "mqtt_ip" in query_components.keys():
                        my_config["mqtt_ip"] = urllib.parse.unquote(query_components["mqtt_ip"])
                    if "mqtt_port" in query_components.keys():
                        my_config["mqtt_port"] = urllib.parse.unquote(query_components["mqtt_port"])
                    if "mqtt_ha_topic" in query_components.keys():
                        my_config["mqtt_ha_topic"] = urllib.parse.unquote(query_components["mqtt_ha_topic"])
                    if "mqtt_base_topic" in query_components.keys():
                        my_config["mqtt_base_topic"] = urllib.parse.unquote(query_components["mqtt_base_topic"])
                    if "mqtt_user" in query_components.keys():
                        my_config["mqtt_user"] = urllib.parse.unquote(query_components["mqtt_user"])
                    if "mqtt_password" in query_components.keys():
                        my_config["mqtt_password"] = urllib.parse.unquote(query_components["mqtt_password"])
                            
                    write_config()
                    mqtt_test_working = test_mqtt()
                    write_sub_head_line (self, lang["config_mystron2ha"])
                    self.wfile.write(bytes("<center><form id=\"config_form\" action=\"webif\" method=\"get\">", "utf-8"))
                    self.wfile.write(bytes("<input type=\"hidden\" id= \"action\" name= \"action\" value=\"m2h_config\">", "utf-8"))
                    self.wfile.write(bytes("<input type=\"hidden\" id= \"password\" name= \"password\" value=\""+urllib.parse.quote(given_password)+"\">", "utf-8"))
                    self.wfile.write(bytes("<div style=\"margin-left:50px; margin-right:50px ; width:80%;\">", "utf-8"))
                    write_input_text (self, "mystrom2ha_ip", "mystrom2ha_ip", lang["mystrom2ha_ip"], my_config["mystrom2ha_ip"], True)
                    write_input_text (self, "mqtt_ip", "mqtt_ip", lang["mqtt_ip"], my_config["mqtt_ip"], True)
                    write_input_text (self, "mqtt_port", "mqtt_port", lang["mqtt_port"], my_config["mqtt_port"], True)
                    write_input_text (self, "mqtt_base_topic", "mqtt_base_topic", lang["mqtt_base_topic"], my_config["mqtt_base_topic"], True)
                    write_input_text (self, "mqtt_ha_topic", "mqtt_ha_topic", lang["mqtt_ha_topic"], my_config["mqtt_ha_topic"], True)
                    write_input_text (self, "mqtt_user", "mqtt_user", lang["mqtt_user"], my_config["mqtt_user"], False)
                    write_input_text (self, "mqtt_password", "mqtt_password", lang["mqtt_password"], my_config["mqtt_password"], False)
                    self.wfile.write(bytes("</div>", "utf-8"))
                    if mqtt_test_working :
                        write_sub_head_line (self, lang["mqtt_connection_ok"])
                    else:
                        write_sub_head_line (self, lang["mqtt_connection_nok"])
                    self.wfile.write(bytes("<br><input type=\"submit\" class='btn btn-primary' value=\"" + lang['update'] + "\" />", "utf-8"))
                    self.wfile.write(bytes("&nbsp;<a href='/webif?password=" + urllib.parse.quote(given_password) +"' class='btn btn-primary'>" + lang['back'] + "</a> \n", "utf-8"))
                    self.wfile.write(bytes("</form></center><br><br>", "utf-8"))

                else:
                    self.wfile.write(bytes("else action", "utf-8"))
            else:
                self.wfile.write(bytes("<center><a class='btn btn-primary' href='/webif?action=m2h_config&password=" + urllib.parse.quote(given_password) +"'>1. "+lang['config_mystron2ha']+"</a></center>", "utf-8"))
                self.wfile.write(bytes("<p></p>", "utf-8"))
                self.wfile.write(bytes("<center><a class='btn btn-primary' href='/webif?action=search_button&password=" + urllib.parse.quote(given_password) +"'>2. "+lang['add_button']+"</a></center>", "utf-8"))


            write_web_footer_page (self)

        elif self.path == '/start_button_search' :
            button_search_running = True
            set_button_ips(self)
            button_search_running = False
            if (len(button_ips) < 1 ):
                write_sub_head_line (self, lang["no_button_found"])
                self.wfile.write(bytes("<center><button class='btn btn-primary' onclick=\"start_search(); update_state(); \">"+lang['button_search']+"</button>", "utf-8"))
                self.wfile.write(bytes("&nbsp;<button class='btn btn-primary' onclick=\"history.back(); \">"+lang['back']+"</button></center>\n", "utf-8"))

                self.wfile.write(bytes("<p></p><form id=\"program_button_ip_form\" action=\"webif\" method=\"get\">", "utf-8"))
                self.wfile.write(bytes("<input type=\"hidden\" id= \"action\" name= \"action\" value=\"program_button_execute\">", "utf-8"))
                self.wfile.write(bytes("<input type=\"hidden\" id= \"password\" name= \"password\" value=\""+urllib.parse.quote(given_password)+"\">", "utf-8"))
                self.wfile.write(bytes("<div style=\"margin-left:50px; margin-right:50px ; width:100%;\"><table><tr><td>", "utf-8"))
                write_input_text (self, "button_ip", "button_ip", lang["button_ip"], "", True)
                self.wfile.write(bytes("</td><td><center><input type=\"submit\" class='btn btn-primary' value=\"" + lang['program_button'] + "\" /></center>", "utf-8"))
                self.wfile.write(bytes("</td></tr></table></div></form>", "utf-8"))


            else:
                write_remark (self, lang["search_finished"])
                self.wfile.write(bytes("", "utf-8"))
                self.wfile.write(bytes("<center><a class='btn btn-primary' href='/webif?action=program_button_start&password="+urllib.parse.quote(given_password)+"' class='btn btn-primary'>" + lang['continue'] + "</a> \n", "utf-8"))
                self.wfile.write(bytes("&nbsp;<button class='btn btn-primary' onclick=\"history.back(); \">"+lang['back']+"</button></center>\n", "utf-8"))

        elif self.path == '/button_search_state' :
            global the_percentage
            self.wfile.write(bytes(the_percentage, "utf-8"))
        
        elif self.path == '/exit' :
            end_ha2mqtt = True
            write_web_top_page (self, "/?x=")
            write_remark(self,"Goodbye!")
            write_web_footer_page (self)
            logging.info("Exit ... ending mystrom2mqtt")
        elif self.path == '/test' :
            write_web_top_page (self, "/?x=")
            self.wfile.write(bytes("ok", "utf-8"))
            write_web_footer_page (self)
            logging.info("test request content connection")

        elif self.path.startswith( '/button_report' ):
            print("hier button_report, path:" + self.path)
            done_trigger="done"

            if "mac" in query_components.keys() and "action" in query_components.keys():
                #request from myStrom button
                if "battery" in query_components.keys():
                    #is Gen1
                    the_mac = query_components["mac"]                    
                    the_button_name = "myStrom_Button_Gen1_"+the_mac
                    the_battery = query_components["battery"]                    
                    the_action = query_components["action"]
                    the_wheel = "0"
                    the_trigger = ""              
                    if the_action == "1":
                        the_trigger="single"
                    elif the_action == "2":
                        the_trigger="double"
                    elif the_action == "3":
                        the_trigger="long"
                    elif the_action == "4":
                        the_trigger="touch"
                    elif the_action == "5":
                        the_wheel = int(query_components["wheel"])
                        if the_wheel < 0 :
                            the_trigger="turn_left"
                        else:
                            the_trigger="turn_right"
                    elif the_action == "6":
                        the_trigger="battery"
                    elif the_action == "11":
                        the_trigger="turn_ended"

                    # Actions:
                    # SINGLE = 1
                    # DOUBLE=2
                    # LONG=3
                    # TOUCH=4
                    # WHEEL=5
                    # WHEEL_FINAL=11
                    # BATTERY=6              

                    # Now MQTT to trigger HA
                    # print("hier: button request:"+the_response_json)
                    try:
                        the_toplevel_topic = my_config["mqtt_base_topic"]
                        the_topic = the_toplevel_topic +"/button/"
                        try:
                            the_mqtt_client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2,"mystrom2ha_client_"+the_mac)
                        except:
                            the_mqtt_client = mqtt_client.Client("mystrom2ha_client_"+the_mac)
                        if my_config["mqtt_user"] != "":
                            the_mqtt_client.username_pw_set(my_config["mqtt_user"], my_config["mqtt_password"])
                        the_mqtt_client.connect(my_config["mqtt_ip"], port=int(my_config["mqtt_port"]), keepalive=60, bind_address="")
                        the_mqtt_client.publish(the_topic+the_mac+"/action",the_trigger)
                        the_mqtt_client.publish(the_topic+the_mac+"/action",done_trigger)
                        if the_action == "5":
                            the_mqtt_client.publish(the_topic+the_mac+"/action/turn",str(the_wheel))
                        the_mqtt_client.publish(the_topic+the_mac+"/battery",the_battery)
                        the_mqtt_client.publish(the_topic+the_mac+"/json","{\"action\":\"" + the_trigger + "\",\"name\":\""+the_button_name+"\",\"mac\":\""+the_mac+"\"}")
                        the_mqtt_client.publish(the_topic+the_mac+"/json","{\"action\":\"" + done_trigger + "\",\"name\":\""+the_button_name+"\",\"mac\":\""+the_mac+"\"}")
                        the_homeassistant_topic = my_config["mqtt_ha_topic"]
                        if (the_homeassistant_topic.endswith("/")):
                            the_homeassistant_topic = the_homeassistant_topic[:-1]
                        the_mqtt_client.publish(the_homeassistant_topic+"/sensor/"+the_mac+"/battery/config","{\"device\": {\"identifiers\":[\""+the_mac+"\"], \"name\":\""+the_button_name+"(mystrom)\",\"model\":\"button"+"\",\"manufacturer\":\"myStrom\"},\"device_class\": \"battery\", \"entity_category\":\"diagnostic\", \"enabled_by_default\": true, \"name\": \"mystrom_"+the_button_name+"_battery\",  \"state_class\":  \"measurement\", \"unique_id\":\""+the_mac+"_battery\", \"state_topic\": \""+the_topic+the_mac+"/battery"+"\", \"unit_of_measurement\": \"%\" }")
                        the_mqtt_client.publish(the_homeassistant_topic+"/sensor/"+the_mac+"/action/config","{\"device\": {\"identifiers\":[\""+the_mac+"\"], \"name\":\""+the_button_name+"(mystrom)\",\"model\":\"button"+"\",\"manufacturer\":\"myStrom\"}, \"enabled_by_default\": true, \"state_topic\": \""+the_topic+the_mac+"/json\", \"name\": \"mystrom_"+the_button_name+"_action\", \"unique_id\":\""+the_mac+"_action\", \"value_template\": \"{{ value_json.action}}\" }")

                    except Exception as ex:
                        logging.error("error button_report Gen1 - "+str(ex))

                elif "bat" in query_components.keys():
                    #Gen2
                    the_mac = query_components["mac"]                    
                    the_name = "myStrom_Button_Gen2_"+the_mac
                    the_voltage = float(query_components["bat"])
                    if the_voltage > 4.0:
                        the_battery = "100"
                    elif the_voltage < 3.0:
                        the_battery = "0"
                    else:
                        the_battery = str (  round(  (the_voltage - 3.0) * 100 / ( 4.0 - 3.0)  )  )
                    the_action = query_components["action"]
                    the_sub_button = query_components["index"]
                    the_index_string = query_components["index"]+"/"
                    the_index = query_components["index"]
                    the_temp = query_components["temp"]
                    the_rh = query_components["rh"]
                    the_trigger = ""              
                    if the_action == "1":
                        the_trigger="single"
                    elif the_action == "2":
                        the_trigger="double"
                    elif the_action == "3":
                        the_trigger="long"
                    elif the_action == "6":
                        the_trigger="battery"
                    
                    # Actions:
                    # SINGLE = 1
                    # DOUBLE=2
                    # LONG=3
                    # TOUCH=4
                    # WHEEL=5
                    # WHEEL_FINAL=11
                    # BATTERY=6              

                    # Now HA Mqtt
                    try:
                        the_toplevel_topic = my_config["mqtt_base_topic"]
                        the_topic = the_toplevel_topic +"/button/"
                        try:
                            the_mqtt_client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2,"mystrom2ha_client_"+the_mac)
                        except:
                            the_mqtt_client = mqtt_client.Client("mystrom2ha_client_"+the_mac)
                        if my_config["mqtt_user"] != "":
                            the_mqtt_client.username_pw_set(my_config["mqtt_user"], my_config["mqtt_password"])
                        the_mqtt_client.connect(my_config["mqtt_ip"], port=int(my_config["mqtt_port"]), keepalive=60, bind_address="")
                        the_mqtt_client.publish(the_topic+the_mac+"/action",the_index + "-" + the_trigger)
                        the_mqtt_client.publish(the_topic+the_mac+"/action",the_index + "-" + done_trigger)
                        the_mqtt_client.publish(the_topic+the_mac+"/temp",the_temp)
                        the_mqtt_client.publish(the_topic+the_mac+"/rh",the_rh)
                        the_mqtt_client.publish(the_topic+the_mac+"/battery",the_battery)
                        the_mqtt_client.publish(the_topic+the_mac+"/name",the_name)
                        the_mqtt_client.publish(the_topic+the_mac+"/json","{\"action\":\"" + the_index + "-" + the_trigger + "\",\"name\":\""+the_name+"\",\"mac\":\""+the_mac+"\", \"temp\":\""+the_temp+"\", \"rh\":\""+the_rh+"\"}")
                        the_mqtt_client.publish(the_topic+the_mac+"/json","{\"action\":\"" + the_index + "-" + done_trigger + "\",\"name\":\""+the_name+"\",\"mac\":\""+the_mac+"\", \"temp\":\""+the_temp+"\", \"rh\":\""+the_rh+"\"}")
                        the_homeassistant_topic = my_config["mqtt_ha_topic"]
                        if (the_homeassistant_topic.endswith("/")):
                            the_homeassistant_topic = the_homeassistant_topic[:-1]
                        the_mqtt_client.publish(the_homeassistant_topic+"/sensor/"+the_mac+"/battery/config","{\"device\": {\"identifiers\":[\""+the_mac+"\"], \"name\":\""+the_name+"(mystrom)\",\"model\":\"Button plus Gen2\",\"manufacturer\":\"myStrom\"},\"device_class\": \"battery\", \"entity_category\":\"diagnostic\", \"enabled_by_default\": true, \"name\": \"mystrom_"+the_name+"_battery\",  \"state_class\":  \"measurement\", \"unique_id\":\""+the_mac+"_battery\", \"state_topic\": \""+the_topic+the_mac+"/battery"+"\", \"unit_of_measurement\": \"%\" }")
                        the_mqtt_client.publish(the_homeassistant_topic+"/sensor/"+the_mac+"/action/config","{\"device\": {\"identifiers\":[\""+the_mac+"\"], \"name\":\""+the_name+"(mystrom)\",\"model\":\"Button plus Gen2\",\"manufacturer\":\"myStrom\"}, \"enabled_by_default\": true, \"state_topic\": \""+the_topic+the_mac+"/json\", \"name\": \"mystrom_"+the_name+"_action\", \"unique_id\":\""+the_mac+"_action\", \"value_template\": \"{{ value_json.action}}\" }")
                        the_mqtt_client.publish(the_homeassistant_topic+"/sensor/"+the_mac+"/temp/config","{\"device\": {\"identifiers\":[\""+the_mac+"\"], \"name\":\""+the_name+"(mystrom)\",\"model\":\"Button plus Gen2\",\"manufacturer\":\"myStrom\"}, \"enabled_by_default\": true, \"state_topic\": \""+the_topic+the_mac+"/json\", \"name\": \"mystrom_"+the_name+"_temp\", \"unique_id\":\""+the_mac+"_temp\", \"value_template\": \"{{ value_json.temp}}\" }")

                    except Exception as ex:
                        logging.error("error button_report Gen2 - "+str(ex))

                elif "value" in query_components.keys():
                    #is PIR
                    the_mac = query_components["mac"]
                    the_name = "myStrom_PIR_"+the_mac                    
                    the_light_intensity = query_components["value"]                    
                    the_action = query_components["action"]
                    if the_action == "8":
                        the_trigger="rise"
                    elif the_action == "9":
                        the_trigger="fall"
                    elif the_action == "14":
                        the_trigger="night"
                    elif the_action == "15":
                        the_trigger="twilight"
                    elif the_action == "16":
                        the_trigger="day"

                    # Now MQTT
                    try:
                        the_toplevel_topic = my_config["mqtt_base_topic"]
                        the_topic = the_toplevel_topic +"/button/"
                        try:
                            the_mqtt_client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2,"mystrom2ha_client_"+the_mac)
                        except:
                            the_mqtt_client = mqtt_client.Client("mystrom2ha_client_"+the_mac)
                        if my_config["mqtt_user"] != "":
                            the_mqtt_client.username_pw_set(my_config["mqtt_user"], my_config["mqtt_password"])
                        the_mqtt_client.connect(my_config["mqtt_ip"], port=int(my_config["mqtt_port"]), keepalive=60, bind_address="")
                        the_mqtt_client.publish(the_topic+the_mac+"/action",the_trigger)
                        the_mqtt_client.publish(the_topic+the_mac+"/action",done_trigger)
                        the_mqtt_client.publish(the_topic+the_mac+"/name",the_name)
                        the_mqtt_client.publish(the_topic+the_mac+"/light",the_light_intensity)
                        the_mqtt_client.publish(the_topic+the_mac+"/json","{\"action\":\"" + the_trigger + "\",\"name\":\""+the_name+"\",\"mac\":\""+the_mac+"\", \"light\":\""+the_light_intensity+"\" }")
                        the_mqtt_client.publish(the_topic+the_mac+"/json","{\"action\":\"" + done_trigger + "\",\"name\":\""+the_name+"\",\"mac\":\""+the_mac+"\", \"light\":\""+the_light_intensity+"\" }")
                        the_homeassistant_topic = my_config["mqtt_ha_topic"]
                        if (the_homeassistant_topic.endswith("/")):
                            the_homeassistant_topic = the_homeassistant_topic[:-1]
                        the_mqtt_client.publish(the_homeassistant_topic+"/sensor/"+the_mac+"/motion/config","{\"device\": {\"identifiers\":[\""+the_mac+"\"], \"name\":\""+the_name+"(mystrom)\",\"model\":\"PIR\",\"manufacturer\":\"myStrom\"}, \"enabled_by_default\": true, \"state_topic\": \""+the_topic+the_mac+"/json\", \"name\": \"mystrom_"+the_name+"_motion\", \"unique_id\":\""+the_mac+"_motion\", \"value_template\": \"{{ value_json.action}}\" }")
                        the_mqtt_client.publish(the_homeassistant_topic+"/sensor/"+the_mac+"/light/config","{\"device\": {\"identifiers\":[\""+the_mac+"\"], \"name\":\""+the_name+"(mystrom)\",\"model\":\"PIR\",\"manufacturer\":\"myStrom\"}, \"enabled_by_default\": true, \"state_topic\": \""+the_topic+the_mac+"/json\", \"name\": \"mystrom_"+the_name+"_light\", \"unique_id\":\""+the_mac+"_light\", \"value_template\": \"{{ value_json.light}}\" }")
                                
                    except Exception as ex:
                        logging.error("error button_report PIR - "+str(ex))
            ### End button_report


        else:
            # loginhier
            write_web_top_page (self, "/?top=")
            self.wfile.write(bytes("<center><img src=\"/login_icon.jpg\" eight=\"270\" width=\"270\">", "utf-8"))
            self.wfile.write(bytes("<h2>"+lang['login']+"</h2>", "utf-8"))
            write_remark (self, lang['login_text'] )
            if wrong_password :
                write_remark (self, lang['login_failed'] )
            self.wfile.write(bytes("<form id=\"login_form\" action=\"webif\" method=\"get\">", "utf-8"))
            self.wfile.write(bytes("<div style=\"margin-left:50px; margin-right:50px ; width:80%;\">", "utf-8"))
            write_input_text (self, "password", "password", lang["password"], "", True)
            self.wfile.write(bytes("</div>", "utf-8"))
            self.wfile.write(bytes("<br><center><input type=\"submit\" class='btn btn-primary' value=\"" + lang['do_login'] + "\" />  </center>\n", "utf-8"))
            self.wfile.write(bytes("</form></center>", "utf-8"))
            write_web_footer_page (self)
            logging.info("login request")




if __name__ == "__main__":

    my_local_ip = get_local_ip()
    try:
        if ('MYSTROM2HA_ACCESS_PASSWORD' in os.environ):
            access_password = os.environ.get('MYSTROM2HA_ACCESS_PASSWORD')
        else:
            access_password = 'mystrom2ha'

    except Exception:
        access_password = 'mystrom2ha'

    format = "%(asctime)s - MyStrom2HA: %(message)s"
    logging.basicConfig(format=format, level=logging.ERROR,
                        datefmt="%H:%M:%S", filename=get_script_directory() + '/mystrom2ha.log', filemode='w')
    read_config()

    button_ips = []
    the_found_button_type = {}
    the_found_button_mac = {}

    print("")
    print("##############################################")
    the_title = "MyStrom2HA"
    print("#" + the_title.center(44) +"#")
    print("#                 access via                 #")
    the_url = "http://" + my_local_ip + ":" + str(button_request_port)
    print("#"+ the_url.center(44)  + "#")
    print("##############################################")
    logging.error("Starting mystrom2ha on "+the_url)

    # start content server
    # Create the content server socket.
    addr = ('', button_request_port)
    sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(addr)
    sock.listen(5)

    #start 20 listening threads for the socket
    [button_thread(i) for i in range(20)]

    logging.info("request answer threads started ... ")

    while end_ha2mqtt != True:
        sleep_time = 5
        time.sleep(sleep_time)

    logging.info("server done.")

        
logging.error("ha2mqtt stopped gracefully.")
