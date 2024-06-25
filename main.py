import json, network, rp2, time, dht, socket
from machine import Pin

# DHT setup
sensor = dht.DHT22(Pin(config["dht_pin"]))

while not wlan.isconnected() and wlan.status() >= 0:
 print(".")
 time.sleep(1)

print(wlan.ifconfig())

def getHTTPMetrics(data: dict):
    return str(f"""
    # HELP dht22_humidity Humidity measured by the DHT22 sensor.
    # TYPE dht22_humidity gauge
    dht22_humidity {data['humidity']}
    # HELP dht22_temperature Temperature measured by the DHT22 sensor.
    # TYPE dht22_temperature gauge
    dht22_temperature {data["temperature"]}
    """)

def setupHTTPServer():
    """function to start a socket on port 80 to be used as an HTTP server"""
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    global HttpSocket
    HttpSocket = socket.socket()
    HttpSocket.bind(addr)
    HttpSocket.listen(1)

def saveConfig():
    """function to save the config dict to the JSON file"""
    with open("config.json", "w") as f:
        json.dump(config, f)

def loadConfig():
    """function to load the config dict from the JSON file"""
    global config
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except:
        print("Failed to load config. Exiting.")
        exit(1)

def setupWifi():
    """"function to configure the WiFi driver and connect to the specified network in the configuration"""
    # Country
    # https://en.wikipedia.org/wiki/ISO_3166-2
    rp2.country(config["wifi_country"])

    global wlan
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # Disable WiFi "power-saving" to allow for fast response times when network monitor requests it
    wlan.config(pm = 0xa11140)

    wlan.connect(config["wifi_ssid"], config["wifi_password"])


def getData(sensor: dht.DHT22 | dht.DHT11):
    """function to get the temperature and humidity from the DHT11/22 sensor"""
    try:
        sensor.measure()
        return {
            "temperature": sensor.temperature(),
            "humidity": sensor.humidity()
        }
    except:
        return {
            "temperature": None,
            "humidity": None
        }
    

pastData = {
    "temperature": None,
    "humidity": None,
    "last_updated": 0
}
def main():
    """main function"""
    global config
    global sensor

    # Load the configuration
    loadConfig()

    # Setup the WiFi driver
    setupWifi()


    while True:
        data = pastData

        # Update data every 2 seconds
        if time.time() - pastData.get("last_updated", 0) > 2:
            data = getData(sensor)
            pastData = data
            data["last_updated"] = time.time()
        
        try:
            cl, addr = HttpSocket.accept()
            print('Client connected from', addr)
            request = cl.recv(1024)
            print(request)

            request = str(request)[0:50] # The [0:50] avoids getting the url directory from referer 
            
            response = getHTTPMetrics(data)

            cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            cl.send(response)
            cl.close()

        except OSError as e:
            cl.close()
            HttpSocket.close()
            print('connection closed')

main()
