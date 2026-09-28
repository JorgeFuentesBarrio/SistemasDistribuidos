import os
import json
import time
import paho.mqtt.client as mqtt

BROKER_HOST = os.getenv("BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("BROKER_PORT", 1883))
ID = os.getenv("COSECHADORA_ID", 1)

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[COSECHADORA {ID}] Conectada al broker en {BROKER_HOST}:{BROKER_PORT}")
    client.subscribe("central-computer", qos=1)
    
    # Ejemplo
    posicion_inicial = 100
    peticion = {"id": ID, "pos": posicion_inicial}
    client.publish("tractor", json.dumps(peticion), qos=1)
    print(f"[COSECHADORA {ID}] Petición de descarga enviada: {peticion}")

def on_message(client, userdata, msg):
    print(f"[COSECHADORA {ID}] Mensaje recibido de la central: {msg.payload.decode('utf-8')}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"cosechadora_{ID}")
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
client.loop_forever()