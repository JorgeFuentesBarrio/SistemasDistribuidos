import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_HOST = os.getenv("DB_HOST", "roach1")
DB_PORT = int(os.getenv("DB_PORT", 26257))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "defaultdb")

def obtener_conexion():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME,
        cursor_factory=RealDictCursor
    )

def init_db():
    conn = obtener_conexion()
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS asignaciones (
                id SERIAL PRIMARY KEY,
                cosechadora_id VARCHAR(10) NOT NULL,
                camion_id VARCHAR(10) NOT NULL,
                fecha_asignacion TIMESTAMPTZ DEFAULT clock_timestamp(),
                distancia FLOAT NOT NULL,
                estado VARCHAR(20) DEFAULT 'ASIGNADO'
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetria (
                id SERIAL PRIMARY KEY,
                tipo_vehiculo VARCHAR(20) NOT NULL,
                vehiculo_id VARCHAR(10) NOT NULL,
                lat FLOAT NOT NULL,
                lon FLOAT NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT clock_timestamp()
            );
            """)
        print("[DB] Tablas 'asignaciones' y 'telemetria' inicializadas correctamente en CockroachDB.")
    finally:
        conn.close()

def guardar_telemetria(tipo_vehiculo, vehiculo_id, lat, lon):
    conn = obtener_conexion()
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO telemetria (tipo_vehiculo, vehiculo_id, lat, lon) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (tipo_vehiculo, str(vehiculo_id), float(lat), float(lon)))
    finally:
        conn.close()

def registrar_mision(cosechadora_id, camion_id, distancia):
    conn = obtener_conexion()
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO asignaciones (cosechadora_id, camion_id, distancia) VALUES (%s, %s, %s)"
            cursor.execute(sql, (str(cosechadora_id), str(camion_id), float(distancia)))
            print(f"[DB] Misión registrada: Cosechadora {cosechadora_id} -> Camión {camion_id} (Distancia: {distancia})")
    finally:
        conn.close()