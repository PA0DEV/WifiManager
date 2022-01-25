#
# name: Phillip Ahlers 
# created:  25.1.2022
#
#
#
# use:
#  XXX
# 
# version: 2022_1_25_XXX
# designed and tested on ESP32 TTGO whith XXX

import network, socket, ure, time, json


## general settings ##
ap_ssid = "PA0DEV-ESP"
ap_pass = "12345678"
ap_auth = 3     # WPA2

wifiSta = network.WLAN(network.STA_IF)
wifiAp = network.WLAN(network.AP_IF)

serverSocket = None

def getConnection():
    """ return a working WLAN(STA_IF) interface or none """
    # First check if there already is any connection:
    if wifiSta.isconnected():
        return wifiSta

    connected = False

    try:
        # ESP might take some time to connect to wifi
        time.sleep(3)
        if wifiSta.isconnected():
            return wifiSta

        # look for known profiles
        profiles = getProfiles()

        # scan for available networks
        wifiAp.active(True)
        networks = wifiAp.scan()

        # compare known networks to found ones and connect if match
        AUTHMODE = {0: "open", 1: "WEP", 2: "WPA-PSK", 3: "WPA2-PSK", 4: "WPA/WPA2-PSK"}
        
        for ssid, bssid, channel, rssi, authmode, hidden in sorted(networks, key=lambda x: x[3], reverse=True):
            ssid = ssid.decode('utf-8')
            encrypted = authmode > 0
            # [DEBUG] print("ssid: %s chan: %d rssi: %d authmode: %s" % (ssid, channel, rssi, AUTHMODE.get(authmode, '?')))
            if encrypted:
                for i in range(len(profiles)):
                    if ssid in profiles[i]["ssid"]:
                        connected = connectWifi(ssid, profiles[i]["pass"])
                    else:
                        pass
            else:
                for i in range(len(profiles)):
                    if ssid in profiles[i]["ssid"]:
                        connected = connectWifi(ssid, None)
                    else:
                        pass
            if connected:
                break

    # Handle OS Error exceptions
    except OSError as e:
        print("[WifiMgr] exception", str(e))    

    # if no known network was found, open Config WebServer
    if not connected: 
        connected = startServer()

    # Return working wifi_STA
    return wifiSta if connected else None



def getProfiles(file="profiles.json"):
    '''
        returns a list of dicts of all known profiles [{"ssid": "SSID", "pass": "PASSWORD"}, ... ]
    '''
    # Try opening the prifiles file
    try:
        print("[WifiMgr] Load known profiles: %s" %(file))
        with open(file) as f:
            profiles = json.load(f)
    # if not possible make a new file
    except:
        print("[WifiMgr] No known profiles found! Creating new template")
        with open(file, "w") as f:
            p = {"profiles":[]}

            f.write(json.dumps(p))
            pass
        with open(file) as f:
            profiles = json.load(f)
    profiles = profiles["profiles"]

    # return List of all known Profiles
    return profiles

def addProfile(profile):
    profiles = getProfiles()
    profiles.append(profile) 
    with open("profiles.json", "w") as f:
        p = {"profiles":profiles}
        f.write(json.dumps(p))


def connectWifi(ssid, password):
    wifiSta.active(True)
    if wifiSta.isconnected():
        return None
    print("[WifiMgr] Trying to connect to %s." %ssid)
    wifiSta.connect(ssid, password)
    print("[WifiMgr] ", end="")
    for retry in range(100):
        connected = wifiSta.isconnected()
        if connected:
            break
        time.sleep(0.1)
        print("#", end="")
    if connected:
        print("\n[WifiMgr] Connected to wifi %s" %ssid)
        print("[WifiMgr] Device IP:  %s" %(wifiSta.ifconfig()[0]))
    else:
        print("\n[WifiMgr] Could not connect to wifi %s" %ssid)
    return connected

def stopServer():
    global serverSocket

    if serverSocket:
        serverSocket.close()
        serverSocket = None

def send_header(client, status_code=200, content_length=None ):
    client.sendall("HTTP/1.0 {} OK\r\n".format(status_code))
    client.sendall("Content-Type: text/html\r\n")
    if content_length is not None:
      client.sendall("Content-Length: {}\r\n".format(content_length))
    client.sendall("\r\n")

def send_response(client, payload, status_code=200):
    content_length = len(payload)
    send_header(client, status_code, content_length)
    if content_length > 0:
        client.sendall(payload)
    client.close()

def handle_root(client):
    wifiSta.active(True)
    ssids = sorted(ssid.decode('utf-8') for ssid, *_ in wifiSta.scan())
    send_header(client)
    client.sendall("""\
        <html>
            <h1 style="color: #5e9ca0; text-align: center;">
                <span style="color: #ff0000;">
                    Wi-Fi Client Setup
                </span>
            </h1>
            <form action="configure" method="post">
                <table style="margin-left: auto; margin-right: auto;">
                    <tbody>
    """)
    while len(ssids):
        ssid = ssids.pop(0)
        client.sendall("""\
                        <tr>
                            <td colspan="2">
                                <input type="radio" name="ssid" value="{0}" />{0}
                            </td>
                        </tr>
        """.format(ssid))
    client.sendall("""\
                        <tr>
                            <td>Password:</td>
                            <td><input name="password" type="password" /></td>
                        </tr>
                    </tbody>
                </table>
                <p style="text-align: center;">
                    <input type="submit" value="Submit" />
                </p>           
        </html>
    """)
    client.close()

def handle_configure(client, request):
    match = ure.search("ssid=([^&]*)&password=(.*)", request)
    print (
        request
    )

    if match is None:
        send_response(client, "Parameters not found", status_code=400)
        return False
    # version 1.9 compatibility
    try:
        ssid = match.group(1).decode("utf-8").replace("%3F", "?").replace("%21", "!").replace("+", " ")
        password = match.group(2).decode("utf-8").replace("%3F", "?").replace("%21", "!")
    except Exception:
        ssid = match.group(1).replace("%3F", "?").replace("%21", "!").replace("%2B", " ")
        password = match.group(2).replace("%3F", "?").replace("%21", "!")

    if len(ssid) == 0:
        send_response(client, "SSID must be provided", status_code=400)
        return False

    if connectWifi(ssid, password):
        response = """\
            <html>
                <center>
                    <br><br>
                    <h1 style="color: #5e9ca0; text-align: center;">
                        <span style="color: #ff0000;">
                            ESP successfully connected to WiFi network %(ssid)s.
                        </span>
                    </h1>
                    <br><br>
                </center>
            </html>
        """ % dict(ssid=ssid)
        send_response(client, response)
        profile = {"ssid": ssid, "pass": password}
        addProfile(profile)

        time.sleep(5)

        return True
    else:
        response = """\
            <html>
                <center>
                    <h1 style="color: #5e9ca0; text-align: center;">
                        <span style="color: #ff0000;">
                            ESP could not connect to WiFi network %(ssid)s.
                        </span>
                    </h1>
                    <br><br>
                    <form>
                        <input type="button" value="Go back!" onclick="history.back()"></input>
                    </form>
                </center>
            </html>
        """ % dict(ssid=ssid)
        send_response(client, response)
        return False

def handle_not_found(client, url):
    send_response(client, "Path not found: {}".format(url), status_code=404)

def startServer(port=80):
    global serverSocket
    addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]

    stopServer()

    wifiSta.active(True)
    wifiAp.active(True)

    wifiAp.config(essid=ap_ssid, password=ap_pass, authmode=ap_auth)

    serverSocket = socket.socket()
    serverSocket.bind(addr)
    serverSocket.listen(1)
    
    print("[WifiMgr] Connect to WiFi ssid %s, default password: %s" %(ap_ssid, ap_pass))
    print("[WifiMgr] and access the ESP via your favorite web browser at %s" %wifiAp.ifconfig()[0])
    print("[WifiMgr] listening on:", addr)

    while True:
        if wifiSta.isconnected():
            return True

        
        client, addr = serverSocket.accept()
        print("[WifiMgr] Client connected from", addr)

        try:
            client.settimeout(5.0)

            request = b""
            try:
                while "\r\n\r\n" not in request:
                    request += client.recv(512)
            except OSError:
                pass

            print("Request is: {}".format(request))
            if "HTTP" not in request:  # skip invalid requests
                continue

            # version 1.9 compatibility
            try:
                url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).decode("utf-8").rstrip("/")
            except Exception:
                url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).rstrip("/")
            print("URL is {}".format(url))

            if url == "":
                handle_root(client)
            elif url == "configure":
                handle_configure(client, request)
            else:
                handle_not_found(client, url)

        finally:
            client.close()

        ...

    