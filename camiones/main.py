import os
import json
import time
import paho.mqtt.client as mqtt

BROKER_HOST = os.getenv("BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("BROKER_PORT", 1883))
ID = os.getenv("CAMION_ID", 1)

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[CAMION {ID}] Conectado al broker.")
    client.subscribe("central-computer", qos=1)
    
    # Ejemplo
    p1 = {"id": 1, "pos": 70, "capacidad": 1}
    p2 = {"id": 2, "pos": 40, "capacidad": 0}
    
    client.publish("truck", json.dumps(p1), qos=1)
    time.sleep(1)
    client.publish("truck", json.dumps(p2), qos=1)
    print(f"[CAMION] Registros iniciales enviados: {p1}, {p2}")

def on_message(client, userdata, msg):
    print(f"[CAMION {ID}] Mensaje de la central: {msg.payload.decode('utf-8')}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"truck_fleet_{ID}")
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
client.loop_forever()