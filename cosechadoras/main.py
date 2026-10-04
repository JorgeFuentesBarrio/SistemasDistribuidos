import json
import os
import random
import threading
import time
import paho.mqtt.client as mqtt

BROKER_HOST = os.getenv("BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("BROKER_PORT", 1883))

NUM_COSECHADORAS = 5

FACTOR_VELOCIDAD = 1.0

TOPIC_PUB = "cosechadoras"
TOPIC_SUB = "asignaciones"

# Coordenadas
LAT_MAX = 38.491662
LAT_MIN = 38.451620
LON_MIN = -4.991992
LON_MAX = -4.951085

def get_coords():
    lat = random.uniform(LAT_MIN, LAT_MAX)
    lon = random.uniform(LON_MIN, LON_MAX)
    return round(lat, 6), round(lon, 6)

def esperar(segundos):
    time.sleep(segundos / FACTOR_VELOCIDAD)

def simular_cosechadora(id_cosechadora, lat, lon):
    tolva = 0
    descargando = False

    def procesar_descarga(cliente_mqtt):
        nonlocal tolva, descargando
        descargando = True
        print(f"[COSECHADORA {id_cosechadora}] Camión asignado -> Descargando tolva...")
        esperar(7)
        tolva = 0
        descargando = False
        print(f"[COSECHADORA {id_cosechadora}] Descarga completada. Tolva al 0%.")

        peticion = {
            "id": id_cosechadora,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "carga": 0,
            "solicita_descarga": 0
        }
        cliente_mqtt.publish(TOPIC_PUB, json.dumps(peticion), qos=1)

    def on_connect(client, userdata, flags, rc, properties=None):
        print(f"[COSECHADORA {id_cosechadora}] Conectada al broker en {BROKER_HOST}:{BROKER_PORT}")
        client.subscribe(TOPIC_SUB, qos=1)

    def on_message(client, userdata, msg):
        nonlocal tolva, descargando
        try:
            mensaje = json.loads(msg.payload.decode("utf-8"))
            texto = mensaje.get("mensaje", "")
            id_asig = mensaje.get("cosechadora_id")

            # Procesar asignación 
            if (id_asig is not None and str(id_asig) == str(id_cosechadora)) or f"cosechadora {id_cosechadora}" in texto.lower():
                if "camion" in texto.lower() or "asignado" in texto.lower():
                    if tolva > 80 and not descargando:
                        threading.Thread(target=procesar_descarga, args=(client,), daemon=True).start()
        except Exception as e:
            print(f"[COSECHADORA {id_cosechadora}] Error leyendo mensaje: {e}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"cosechadora_{id_cosechadora}")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    print(f"[COSECHADORA {id_cosechadora}] INICIADA")

    while True:
        # Simulación de recolección mientras no esté llena por ejemplo añadiendo diez 
        if not descargando and tolva < 100:
            tolva = min(100, tolva + 10)
            print(f"[COSECHADORA {id_cosechadora}] Cosechando... Tolva al {tolva}%")

        peticion = {
            "id": id_cosechadora,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "carga": tolva,
            "solicita_descarga": 1 if (tolva > 80 and not descargando) else 0
        }
        client.publish(TOPIC_PUB, json.dumps(peticion), qos=1)
        
        esperar(3)


def main():
    for i in range(1, NUM_COSECHADORAS + 1):
        c_lat, c_lon = get_coords()
        t = threading.Thread(target=simular_cosechadora, args=(i, c_lat, c_lon), daemon=True)
        t.start()
        esperar(0.3)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDesconectando cosechadoras...")


if __name__ == "__main__":
    main()