import os
import json
import time
import math
import threading
import paho.mqtt.client as mqtt
import database

BROKER_HOST = os.getenv("BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("BROKER_PORT", 1883))

TOPIC_CENTRAL = "central-computer"
TOPICS_SUB = ["cosechadoras", "truck"]

trucks = []
trucks_lock = threading.Lock()

# Control de estado
camiones_ocupados = set()
tiempo_mision = {}             # camion_id -> timestamp inicio de mision (evita mensajes residuales)
cosechadoras_atendidas = {}    # cosechadora_id -> camion_id
cosechadoras_pos = {}
cola_espera = []              # para cosechadoras pendientes de camión


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
    disponibles = []
    for truck in trucks:
        if truck["capacidad"] == 1 and truck["id"] not in camiones_ocupados:
            disponibles.append(truck)
    return disponibles

def camion_in_trucks(trucks, id_camion):
    for index, truck in enumerate(trucks):
        if str(truck["id"]) == str(id_camion):
            return index
    return -1

def disponibilizar_camion(trucks, id_camion, new_capacidad):
    for truck in trucks:
        if str(truck["id"]) == str(id_camion):
            truck["capacidad"] = new_capacidad
    return trucks

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 3)

def asignar_camion_a_cosechadora(client, cos_id, lat, lon):
    """Busca el mejor camión libre y envía la asignación."""
    disponibles = camiones_disponibles(trucks)
    if not disponibles:
        if cos_id not in cola_espera:
            cola_espera.append(cos_id)
            print(f"[CENTRAL] Sin camiones libres. Cosechadora {cos_id} añadida a cola de espera ({len(cola_espera)} en cola).")
            respuesta = {
                "tipo": "COLA",
                "cosechadora_id": cos_id,
                "mensaje": f"Cosechadora {cos_id} en cola de espera."
            }
            client.publish(TOPIC_CENTRAL, json.dumps(respuesta), qos=1)
        return False

    minimum = float("+inf")
    selected_truck = None
    for truck in disponibles:
        distancia = calcular_distancia(lat, lon, truck["lat"], truck["lon"])
        if distancia < minimum:
            minimum = distancia
            selected_truck = truck

    disponibilizar_camion(trucks, selected_truck["id"], 0)
    camiones_ocupados.add(selected_truck["id"])
    tiempo_mision[selected_truck["id"]] = time.time()
    cosechadoras_atendidas[cos_id] = selected_truck["id"]

    database.registrar_mision(
        cosechadora_id=cos_id,
        camion_id=selected_truck["id"],
        distancia=minimum
    )

    respuesta = {
        "tipo": "ASIGNACION",
        "cosechadora_id": cos_id,
        "camion_id": selected_truck["id"],
        "lat": lat,
        "lon": lon,
        "distancia": minimum,
        "mensaje": f"Camión {selected_truck['id']} asignado a cosechadora {cos_id}"
    }
    client.publish("asignaciones", json.dumps(respuesta), qos=1)
    client.publish(TOPIC_CENTRAL, json.dumps(respuesta), qos=1)
    print(f"[CENTRAL] Asignación completada: {respuesta}")
    return True

def on_message(client, userdata, msg):
    global trucks
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        vehiculo_id = data.get("id")
        lat = data.get("lat")
        lon = data.get("lon")
        capacidad = data.get("capacidad")
        solicita_descarga = data.get("solicita_descarga")

        if msg.topic == "truck":
            print(f"[CENTRAL] Camión reportado: {data}")
            camion_liberado = False
            with trucks_lock:
                if vehiculo_id in camiones_ocupados:
                    if capacidad == 1:
                        # Si se asignó hace menos de 4s, es un mensaje residual previo en tránsito por MQTT
                        if time.time() - tiempo_mision.get(vehiculo_id, 0) < 4.0:
                            capacidad = 0
                        else:
                            camiones_ocupados.remove(vehiculo_id)
                            camion_liberado = True
                            print(f"[CENTRAL] Camión {vehiculo_id} disponible de nuevo.")

                truck_idx = camion_in_trucks(trucks, vehiculo_id)
                if truck_idx == -1:
                    trucks.append({"id": vehiculo_id, "lat": lat, "lon": lon, "capacidad": capacidad})
                else:
                    trucks[truck_idx]["lat"] = lat
                    trucks[truck_idx]["lon"] = lon
                    trucks[truck_idx]["capacidad"] = capacidad

                # Si un camión queda libre de forma real, despachar a la siguiente cosechadora en espera
                if camion_liberado and cola_espera:
                    siguiente_cos = cola_espera.pop(0)
                    pos = cosechadoras_pos.get(siguiente_cos)
                    if pos:
                        print(f"[CENTRAL] Despachando camión para cosechadora {siguiente_cos} desde cola de espera.")
                        asignar_camion_a_cosechadora(client, siguiente_cos, pos["lat"], pos["lon"])

            database.guardar_telemetria("truck", vehiculo_id, lat, lon)

        elif msg.topic == "cosechadoras":
            print(f"[CENTRAL] Petición de descarga (Cosechadora): {data}")
            with trucks_lock:
                cosechadoras_pos[vehiculo_id] = {"lat": lat, "lon": lon}

                if solicita_descarga == 1:
                    if vehiculo_id in cosechadoras_atendidas:
                        camion_actual = cosechadoras_atendidas[vehiculo_id]
                        print(f"[CENTRAL] Cosechadora {vehiculo_id} ya tiene asignado el camión {camion_actual}. Petición ignorada.")
                    elif vehiculo_id in cola_espera:
                        pass
                    else:
                        asignar_camion_a_cosechadora(client, vehiculo_id, lat, lon)

                else:
                    if vehiculo_id in cosechadoras_atendidas:
                        camion_asig = cosechadoras_atendidas.pop(vehiculo_id)
                        print(f"[CENTRAL] Cosechadora {vehiculo_id} ha finalizado descarga (camión {camion_asig}).")
                    if vehiculo_id in cola_espera:
                        cola_espera.remove(vehiculo_id)

            database.guardar_telemetria("cosechadoras", vehiculo_id, lat, lon)

    except Exception as e:
        print(f"[CENTRAL] Error procesando payload entrante: {e}")

# Espera e inicialización de BD
wait_db()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="central_coordinator")
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
client.loop_forever()