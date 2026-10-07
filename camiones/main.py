import json
import os
import time
import threading
import random
import paho.mqtt.client as mqtt

BROKER_HOST = os.getenv("BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("BROKER_PORT", 1883))

NUM_CAMIONES = 3
FACTOR_VELOCIDAD = 1.0

TOPIC_PUB = "truck"
TOPIC_SUB = "asignaciones"
TOPIC_NOTIFICACIONES = "asignaciones"

LAT_MAX = 38.491662
LAT_MIN = 38.451620
LON_MIN = -4.991992
LON_MAX = -4.951085

# Coordenadas del silo central
SILO_LAT = 38.471641
SILO_LON = -4.971538


def get_coords():
    lat = random.uniform(LAT_MIN, LAT_MAX)
    lon = random.uniform(LON_MIN, LON_MAX)
    return round(lat, 6), round(lon, 6)


def esperar(segundos):
    time.sleep(segundos / FACTOR_VELOCIDAD)


def simular_camion(camion_id, coords_iniciales):
    lat, lon = coords_iniciales
    capacidad = 1  # 1: libre, 0: ocupado
    en_mision = False
    lock = threading.Lock()

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2, client_id=f"camion_{camion_id}"
    )

    def enviar_estado(c_lat, c_lon, cap):
        estado = {
            "id": camion_id,
            "lat": round(c_lat, 6),
            "lon": round(c_lon, 6),
            "capacidad": cap,
        }
        client.publish(TOPIC_PUB, json.dumps(estado), qos=1)
        print(
            f"[CAMION {camion_id}] Estado -> Lat: {estado['lat']}, Lon: {estado['lon']}, Libre: {cap}"
        )

    def mover_hacia(lat_dest, lon_dest, pasos=25, intervalo=0.6):
        nonlocal lat, lon
        delta_lat = (lat_dest - lat) / pasos
        delta_lon = (lon_dest - lon) / pasos

        for _ in range(pasos):
            lat += delta_lat
            lon += delta_lon
            enviar_estado(lat, lon, capacidad)
            esperar(intervalo)

        lat = lat_dest
        lon = lon_dest
        enviar_estado(lat, lon, capacidad)

    def ejecutar_mision(dest_lat, dest_lon, cosechadora_id):
        nonlocal capacidad, en_mision
        with lock:
            if en_mision:
                return
            en_mision = True
            capacidad = 0

        print(f"[CAMION {camion_id}] En camino a cosechadora {cosechadora_id}...")
        enviar_estado(lat, lon, capacidad)
        mover_hacia(dest_lat, dest_lon, pasos=25, intervalo=0.6)

        print(f"[CAMION {camion_id}] Llegada a cosechadora {cosechadora_id}. Iniciando transferencia...")
        aviso_llegada = {
            "tipo": "LLEGADA",
            "cosechadora_id": cosechadora_id,
            "camion_id": camion_id
        }
        client.publish(TOPIC_NOTIFICACIONES, json.dumps(aviso_llegada), qos=1)

        esperar(4.0)

        print(f"[CAMION {camion_id}] Grano cargado. Desplazándose hacia el silo central...")
        mover_hacia(SILO_LAT, SILO_LON, pasos=25, intervalo=0.6)

        print(f"[CAMION {camion_id}] Descargando tolva en el silo...")
        esperar(3.0)

        with lock:
            capacidad = 1
            en_mision = False

        print(f"[CAMION {camion_id}] Tolva vacía. Disponible en el silo central.")
        enviar_estado(lat, lon, capacidad)

    def on_connect(client, userdata, flags, rc, properties=None):
        print(f"[CAMION {camion_id}] Conectado a Mosquitto en {BROKER_HOST}:{BROKER_PORT}")
        client.subscribe(TOPIC_SUB, qos=1)

    def on_message(client, userdata, msg):
        try:
            mensaje = json.loads(msg.payload.decode("utf-8"))
            tipo = mensaje.get("tipo", "ASIGNACION")

            # Solo procesar mensajes de nueva asignación dirigidos a este camión
            if tipo == "ASIGNACION":
                camion_asignado = mensaje.get("camion_id")
                if camion_asignado is not None and str(camion_asignado) == str(camion_id):
                    if not en_mision:
                        cosechadora_id = mensaje.get("cosechadora_id")
                        dest_lat = float(mensaje.get("lat"))
                        dest_lon = float(mensaje.get("lon"))

                        t = threading.Thread(
                            target=ejecutar_mision,
                            args=(dest_lat, dest_lon, cosechadora_id),
                            daemon=True,
                        )
                        t.start()
                    else:
                        print(f"[CAMION {camion_id}] Asignación ignorada: actualmente en misión.")
        except Exception as e:
            print(f"[CAMION {camion_id}] Error procesando mensaje MQTT: {e}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    while True:
        if not en_mision:
            enviar_estado(lat, lon, capacidad)
        esperar(3.0)


def main():
    print(f"Iniciando flota de {NUM_CAMIONES} camiones...")
    for i in range(1, NUM_CAMIONES + 1):
        coords = get_coords()
        hilo = threading.Thread(target=simular_camion, args=(i, coords), daemon=True)
        hilo.start()
        esperar(0.2)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDeteniendo camiones...")


if __name__ == "__main__":
    main()