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

# Coordenadas
LAT_MAX = 38.491662
LAT_MIN = 38.451620
LON_MIN = -4.991992
LON_MAX = -4.951085

# Silo
SILO_LAT = 38.471641
SILO_LON = -4.971538

def get_coords():
    lat = random.uniform(LAT_MIN, LAT_MAX)
    lon = random.uniform(LON_MIN, LON_MAX)
    return round(lat, 6), round(lon, 6)

def esperar(segundos):
    time.sleep(segundos / FACTOR_VELOCIDAD)

def simular_camion(camion_id, coords_base):
    base_lat, base_lon = coords_base
    lat = base_lat
    lon = base_lon
    capacidad = 1  # 1 libre, 0 ocupado
    en_mision = False

    def enviar_estado(c_lat, c_lon, cap):
        estado = {
            "id": camion_id,
            "lat": round(c_lat, 6),
            "lon": round(c_lon, 6),
            "capacidad": cap
        }
        client.publish(TOPIC_PUB, json.dumps(estado), qos=1)
        print(f"[CAMION {camion_id}] Estado enviado -> Lat: {estado['lat']}, Lon: {estado['lon']}, Capacidad: {cap}")

    def mover_hacia(lat_dest, lon_dest, pasos=15):
        nonlocal lat, lon
        delta_lat = (lat_dest - lat) / pasos
        delta_lon = (lon_dest - lon) / pasos

        for _ in range(pasos):
            lat += delta_lat
            lon += delta_lon
            enviar_estado(lat, lon, capacidad)
            esperar(0.3)

    def on_connect(client, userdata, flags, rc, properties=None):
        print(f"[CAMION {camion_id}] Conectado al broker en {BROKER_HOST}:{BROKER_PORT}")
        client.subscribe(TOPIC_SUB, qos=1)

    def on_message(client, userdata, msg):
        nonlocal capacidad, en_mision, lat, lon
        try:
            mensaje = json.loads(msg.payload.decode("utf-8"))
            camion_asignado = mensaje.get("camion_id")

            if camion_asignado is not None and str(camion_asignado) == str(camion_id):
                cosechadora_id = mensaje.get("cosechadora_id", "?")
                dest_lat = mensaje.get("lat", base_lat + 0.003)
                dest_lon = mensaje.get("lon", base_lon + 0.003)

                print(f"[CAMION {camion_id}] Asignación recibida para cosechadora {cosechadora_id}")

                if not en_mision:
                    en_mision = True
                    capacidad = 0
                    enviar_estado(lat, lon, capacidad)

                    print(f"[CAMION {camion_id}] Desplazándose hacia cosechadora {cosechadora_id}...")
                    mover_hacia(dest_lat, dest_lon)

                    print(f"[CAMION {camion_id}] Recibiendo carga de cosechadora...")
                    esperar(2.5)

                    print(f"[CAMION {camion_id}] Desplazándose hacia el silo a descargar...")
                    mover_hacia(SILO_LAT, SILO_LON)

                    esperar(2.0)
                    print(f"[CAMION {camion_id}] Descarga en silo finalizada. Volviendo a base...")
                    mover_hacia(base_lat, base_lon)

                    capacidad = 1
                    en_mision = False
                    print(f"[CAMION {camion_id}] Disponible de nuevo.")
                    enviar_estado(lat, lon, capacidad)
                else:
                    print(f"[CAMION {camion_id}] Ocupado, orden descartada.")

        except Exception as e:
            print(f"[CAMION {camion_id}] Error leyendo mensaje: {e}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"camion_{camion_id}")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    print(f"[CAMION {camion_id}] INICIADO")

    while True:
        if not en_mision:
            enviar_estado(lat, lon, capacidad)
        esperar(3.0)


def main():
    print(f"Iniciando {NUM_CAMIONES} camiones (Factor velocidad: x{FACTOR_VELOCIDAD})...")

    for i in range(1, NUM_CAMIONES + 1):
        coords = get_coords()
        hilo = threading.Thread(target=simular_camion, args=(i, coords), daemon=True)
        hilo.start()
        esperar(0.3)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDesconectando camiones...")


if __name__ == "__main__":
    main()