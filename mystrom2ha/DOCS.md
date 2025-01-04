# MyStrom2ha Addon for Home Assistant

Here you find MyStrom2HA as Home Assistant Addon. To install perform the following the steps

After installing the addon

- Optionally: In Configuration change the password of the webservice and click on 'save'. The default password is 'mystrom2ha'.
- then start the addon
- after the addon has startet open the web ui to configure the integration and add buttons. The address is http://(local ip of ha):32570/
- First go to 1. 'MyStrom2HA Configuration' and enter the MQTT details. With the buttom on the bottom you save the configuration anad test the connection
- Then use 2. 'Add button' to add a button or Motion sensor
  - **Important Info:** Due to security limitations for HA Addons the buttons can not be found automatically but have to be added via the IP address.
  - First you need to use the 'myStrom Button Trouble Shooting Tool' by MyStrom or use the MyStrom app to connect the buttons with the wifi network and then you need to identify the ip address of the button. But make sure to only connect the button to the network and not integrate it to the MyStrom eco system.
  - After adding the button to the network enter the IP address of the button in the field of the MyStrom2HA webui and connect the button. This needs to happen shortly after the button has restarted after the wifi setup.
 
Have fun with MyStrom2HA

