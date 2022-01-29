# created:  25.1.2022
# by PA0DEV
#
# version: 1.2.1
# designed and tested on ESP32 TTGO

""" 
MIT License

Copyright (c) [2022] [PA0DEV]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. 
"""

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
        wifiSta.active(True)
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
                        connected = connectWifi(ssid, profiles[i]["pass"], profiles[i]["dhcp"], profiles[i]["clientIP"], profiles[i]["subnet"], profiles[i]["gateway"],  profiles[i]["dns"])
                    else:
                        pass
            else:
                for i in range(len(profiles)):
                    if ssid in profiles[i]["ssid"]:
                        connected = connectWifi(ssid, None, profiles[i]["dhcp"], profiles[i]["clientIP"], profiles[i]["subnet"], profiles[i]["gateway"],  profiles[i]["dns"])
                    else:
                        pass
            if connected:
                break

    # Handle OS Error exceptions
    except OSError as e:
        print("[WifiMgr] exception", str(e))    

    # if no known network was found, open Config WebServer
    print(connected)
    if not connected: 
        connected = startServer()

    # Return working wifi_STA
    if connected:
        wifiAp.active(False)
        return wifiSta
    else:
        return None



def getProfiles(file="profiles.json"):
    '''
        returns a list of dicts of all known profiles [{"ssid": "SSID", "pass": "PASSWORD", "dhcp": true | false, }, ... ]
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


def connectWifi(ssid, password, dhcp=True, clientIP="", subnet="", gateway="", dns="8.8.8.8"):
    wifiSta.active(False)
    if wifiSta.isconnected():
        return True

    wifiSta.active(True)

    if not dhcp:
        wifiSta.ifconfig((clientIP, subnet, gateway, dns))

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
        # wifiAp.active(False)
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
            <style>
                body{
                    background-color: #1f1f1f; 
                    color: whitesmoke; 
                }
                h1{
                    text-align: center; 
                    font-size: 70px;
                }
                span{
                    color: orangered;
                }
                table, th, td{
                    background-color: whitesmoke;
                    border: 1px solid black;
                    border-collapse: collapse;
                    color: black;
                    font-size: 40px;
                    line-height: 60px;
                }
                table{
                    margin-left: auto;
                    margin-right: auto;
                }
                tr{
                    height: 60px;
                }
                input[type="radio"]{
                    width: 50px; 
                    height: 30px;
                    line-height: 60px;
                    text-align: left;

                }
            </style>
            <script>
                function showHide(){
                    var x = document.getElementById("clientIP");
                    var y = document.getElementById("subnet");
                    var z = document.getElementById("gateway");
                    var w = document.getElementById("dns");

                    var radio = document.getElementsByName("dhcp");

                    if (radio[0].checked){
                        w.style.display = "none";
                        x.style.display = "none";
                        y.style.display = "none";
                        z.style.display = "none";
                    } else if (radio[1].checked) {
                        w.style.display = "table-row";
                        x.style.display = "table-row";
                        y.style.display = "table-row";
                        z.style.display = "table-row";
                    }
                }
            </script>
            <title>ESP-WiFi setup</title>
            <body onload="showHide()">
                        <h1>
                        <span >
                            Wi-Fi Client Setup
                        </span>
                    </h1>
                    <form action="configure" method="post">
                        <table>
                            <tbody>
                                <tr>
                                    <td>DHCP</td>
                                    <td>
                                        <input id="dhcpOff" type="radio" name="dhcp" value="On" checked onchange="showHide()"> On
                                        <input id="dhcpOn" type="radio" name="dhcp" value="Off" onchange="showHide()"> Off
                                    </td>
                                </tr>
                                <tr id="clientIP">
                                    <td style="font-size: 40px; border-right: none;">Device IP:</td>
                                    <td style="width: 300px;"><input pattern="(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$" name="clientIP"  type="text" placeholder="192.168.178.100" style="height: 60px; font-size: 50px;"/></td>
                                </tr>
                                <tr id="subnet">
                                    <td style="font-size: 40px; border-right: none;">Subnetmask:</td>
                                    <td style="width: 300px;"><input pattern="(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$" name="subnet" type="text" placeholder="255.255.255.0" style="height: 60px; font-size: 50px;"/></td>
                                </tr>
                                <tr id="gateway">
                                    <td style="font-size: 40px; border-right: none;">Gateway:</td>
                                    <td style="width: 300px;"><input pattern="(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$" name="gateway" type="text" placeholder="192.168.178.1" style="height: 60px; font-size: 50px;"/></td>
                                </tr>
                                <tr id="dns">
                                    <td style="font-size: 40px; border-right: none;">DNS-server:</td>
                                    <td style="width: 300px;"><input pattern="(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$" name="dns" type="text" placeholder="8.8.8.8" style="height: 60px; font-size: 50px;"/></td>
                                </tr>
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
                                <td colspan="2">
                                    
                                </td>
                            </tr>
                            <tr>
                                <td style="font-size: 40px; border-right: none; width: 300px;">Password:</td>
                                <td style="width: 300px;"><input name="password" type="password" style="height: 60px; font-size: 50px;"/></td>
                            </tr>
                            
                        </tbody>
                    </table>
                    <p style="text-align: center;">
                        <input type="submit" value="Submit" style="height: 60px; width: 200px; font-size: 50px; background-color: whitesmoke; " />
                    </p>
                </form>
        </body>
    </html>
    """)
    client.close()

def handle_configure(client, request):
    regExp = "dhcp=(On|Off)&clientIP=(.*)&subnet=(.*)&gateway=(.*)&dns=(.*)&ssid=([^&]*)&password=(.*)"
    match = ure.search(regExp, request)
    print (
        request
    )

    if match is None:
        send_response(client, "Parameters not found", status_code=400)
        return False
    # version 1.9 compatibility
    try:
        if match.group(1).decode("utf-8") == "On":
            dhcp = True
        else:
            dhcp = False
        clientIP = match.group(2).decode("utf-8")
        subnet = match.group(3).decode("utf-8")
        gateway = match.group(4).decode("utf-8")
        dns = match.group(5).decode("utf-8")
        ssid = match.group(6).decode("utf-8").replace("%3F", "?").replace("%21", "!").replace("+", " ")
        password = match.group(7).decode("utf-8").replace("%3F", "?").replace("%21", "!")
    except Exception:
        if match.group(1).decode("utf-8") == "On":
            dhcp = True
        else:
            dhcp = False
        clientIP = match.group(2)
        subnet = match.group(3)
        gateway = match.group(4)
        dns = match.group(5)
        ssid = match.group(6).replace("%3F", "?").replace("%21", "!").replace("+", " ")
        password = match.group(7).replace("%3F", "?").replace("%21", "!")

    if len(ssid) == 0:
        send_response(client, "SSID must be provided :(", status_code=400)
        return False

    if not dhcp and (len(clientIP) == 0 or len(subnet) == 0 or len(gateway) == 0 or len(dns) == 0):
        send_response(client, "Bad IP configuration :(", status_code=400)
        return False

    if connectWifi(ssid, password, dhcp, clientIP, subnet, gateway, dns):
        response = """\
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <style>
                    body{
                        background-color: #1f1f1f;
                    }
                    h1{
                        color: whitesmoke;
                        text-align: center;
                    }
                </style>
                <title>Connected!</title>
            </head>
            <body>
                <h1>
                    <span>
                        ESP successfully connected to WiFi network %(ssid)s.
                    </span>
                </h1>
            </body>
            </html>
        """ % dict(ssid=ssid)
        send_response(client, response)
        profile = {"ssid": ssid, "pass": password, "dhcp": dhcp, "clientIP": clientIP, "subnet": subnet, "gateway": gateway, "dns": dns}
        addProfile(profile)

        time.sleep(5)
        wifiAp.active(False)
        return True
    else:
        response = """\
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <style>
                    body{
                        background-color: #1f1f1f;
                        align-items: center;
                        margin: auto;
                        display: block;
                        text-align: center;
                    }
                    h1{
                        font-size: 50px;
                        background-color: tomato;
                        color: whitesmoke;
                        text-align: center;
                        margin-bottom: 100px;
                    }
                    input{
                        width: 500px;
                        height: 100px;
                        font-size: 30px;
                    }
                </style>
                <title>Error!</title>
            </head>
            <body>
                <h1>
                    <span>
                        ESP could not connect to WiFi network <br>%(ssid)s
                    </span>
                </h1>
                <form>
                    <input type="button" value="Go Back!" onclick="history.back()">
                </form>
            </body>
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

    