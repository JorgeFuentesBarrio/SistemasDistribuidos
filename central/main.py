import os
import json
import time
import random
import paho.mqtt.client as mqtt
import threading
import database

BROKER_HOST = os.getenv("BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("BROKER_PORT", 1883))

TOPIC_CENTRAL = "central-computer"
TOPICS_SUB = ["cosechadoras", "asignaciones", "truck"]

trucks = []
trucks_lock = threading.Lock()


def wait_db():
    reintentos = 15
    while reintentos > 0:
        try:
            database.init_db()
            break
        except Exception as e:
            print(f"[CENTRAL] Esperando a que MariaDB esté lista... reintentando en 2s ({e})")
            time.sleep(2)
            reintentos -= 1

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[CENTRAL] Conectado al broker MQTT en {BROKER_HOST}:{BROKER_PORT} (Código {rc})")
    for t in TOPICS_SUB:
        client.subscribe(t, qos=1)
        print(f"[CENTRAL] Suscrito al topic: {t}")

def camiones_disponibles(trucks):
    camiones_disponibles = []
    for truck in trucks:
        if truck["capacidad"] == 1:
            camiones_disponibles.append(truck)
    return camiones_disponibles

def camion_in_trucks(trucks):
    index = 0
    for truck in trucks:
        if truck["id"] == id:
            return index
        index = index+1
    return -1

def disponibilizar_camion(trucks, id, new_capacidad):
    for truck in trucks:
        if truck["id"] == id:
            truck["capacidad"] = new_capacidad
    return trucks

def on_message(client, userdata, msg):
    global trucks
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        vehiculo_id = data.get("id")
        posicion = data.get("pos")
        capacidad = data.get("capacidad")
        if msg.topic == "truck":
            print(f"[CENTRAL] Camión reportado: {data}")
            with trucks_lock:
                truck_idx = camion_in_trucks(trucks)
                if truck_idx == -1:
                    trucks.append({"id": vehiculo_id, "pos": posicion, "capacidad": capacidad})
                else:
                    trucks[truck_idx]["capacidad"] = capacidad
            database.guardar_telemetria("truck", vehiculo_id, posicion)
        elif msg.topic == "cosechadoras":
            print(f"[CENTRAL] Petición de descarga (Cosechadora): {data}")
            database.guardar_telemetria("cosechadoras", vehiculo_id, posicion)
            if len(trucks) == 0 or len(camiones_disponibles(trucks)) == 0:
                respuesta = {
                    "tipo": "ERROR",
                    "mensaje": f"No hay camiones disponibles para la cosechadora {vehiculo_id}."
                }
                client.publish(TOPIC_CENTRAL, json.dumps(respuesta), qos=1)
                client.publish("TOPIC_CENTRAL", json.dumps(respuesta), qos=1)
                print(f"[CENTRAL] Sin unidades disponibles para {vehiculo_id}")
            else:
                minimum = float("+inf")
                selected_truck = None
                with trucks_lock:
                    for truck in trucks:
                        distancia = abs(posicion - truck["pos"])
                        if distancia < minimum:
                            minimum = distancia
                            selected_truck = truck
                            disponibilizar_camion(trucks, selected_truck["id"], 0)

                database.registrar_mision(
                    cosechadora_id=vehiculo_id,
                    camion_id=selected_truck["id"],
                    distancia=minimum
                )

                respuesta = {
                    "tipo": "ASIGNACION",
                    "cosechadora_id": vehiculo_id,
                    "camion_id": selected_truck["id"],
                    "distancia": minimum,
                    "mensaje": f"Camión {selected_truck['id']} asignado a cosechadora {vehiculo_id}"
                }
                client.publish("asignaciones", json.dumps(respuesta), qos=1)
                print(f"[CENTRAL] Asignación completada: {respuesta}")

    except Exception as e:
        print(f"[CENTRAL] Error procesando payload entrante: {e}")

# Espera e inicialización de BD
wait_db()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="central_coordinator")
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
client.loop_forever()