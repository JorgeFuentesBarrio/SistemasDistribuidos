import json
import os
import random
import time
import paho.mqtt.client as mqtt

BROKER_HOST = os.getenv("BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("BROKER_PORT", 1883))
ID = os.getenv("COSECHADORA_ID", 1)

TOPIC_PUB = "cosechadoras"
TOPIC_SUB = "asignaciones"

tolva = 0  
posicion = 100  

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[COSECHADORA {ID}] Conectada al broker en {BROKER_HOST}:{BROKER_PORT}")
    client.subscribe(TOPIC_SUB, qos=1)

def on_message(client, userdata, msg):
    global tolva
    try:
        mensaje = json.loads(msg.payload.decode("utf-8"))
        texto = mensaje["mensaje"]
        print(f"[COSECHADORA {ID}] Mensaje recibido de la central: {texto}")
        
        # Procesar asignación 
        if f"cosechadora {ID}" in texto.lower() or f'"cosechadora_id": {ID}' in texto:
            if "camion" in texto.lower() or "asignado" in texto.lower():
                if tolva > 80:
                    print(f"[COSECHADORA {ID}] Camión asignado -> Descargando tolva...")
                    time.sleep(2)
                    tolva = 0
                    print(f"[COSECHADORA {ID}] Descarga completada. Tolva al 0%.")
    except Exception as e:
        print(f"[COSECHADORA {ID}] Error leyendo mensaje: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"cosechadora_{ID}")
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
client.loop_start()

print(f"[COSECHADORA {ID}] INICIADA")

try:
    while True:
        # Simulación de recolección mientras no esté llena por ejemplo añadiendo diez 
        if tolva < 100:
            tolva = min(100, tolva + 10)
            print(f"[COSECHADORA {ID}] Cosechando... Tolva al {tolva}%")

        peticion = {
            "id": ID,
            "pos": posicion,
            "carga": tolva,
            "solicita_descarga":  1 if tolva > 80 else 0
        }
        client.publish(TOPIC_PUB, json.dumps(peticion), qos=1)
        
        time.sleep(3)  

except KeyboardInterrupt:
    print(f"\n[COSECHADORA {ID}] desconectando")
    client.loop_stop()
    client.disconnect()
