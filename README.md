# WifiManager
 

Written in  :   MicroPython

Tested on   :   ESP32

<b>Description : </b> WiFi Manager to find, connect and save wifi credentials

<b>Main features :</b>

- Web based connection manager
- save known Networks and passwords in "profiles.json" (JSON-Format)
- Easy to include in your projects

<b>Usage :</b>

1. copy the wifiManager.py in your project folder
2. import the wifiManager in your boot.py (_recommended_) or main.py 
   
    ```python
    import wifiManager
    ```
3. Run the `getConnection()` method

    ```python
    wlan = wifiManager.getConnection()

    if wlan is None:
        print("[WifiMgr] Could not initialize the network connection.")
        while True:
            pass  # you shall not pass :D
    ```
    The `getMethod()` method will return a working `WLAN(STA_IF)` interface or `None`

4. Run your main code afterwards

<b>Logic: </b>

1. step: check if "profiles.json" contains any reachable networks
2. step: open a web server to configure a new wifi
3. step: save the ssid / password from the configuration to "profiles.json"
4. step: run user code

