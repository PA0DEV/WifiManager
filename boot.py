import wifiManager

wlan = wifiManager.getConnection()

if wlan is None:
    print("[WifiMgr] Could not initialize the network connection.")
    while True:
        pass  # you shall not pass :D
else:
    print("[WifiMgr] ESP OK")

# Main Code starts here, wlan is a working network.WLAN(STA_IF) instance.

while True:
    pass
