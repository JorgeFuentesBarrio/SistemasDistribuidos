import os
import pymysql

DB_HOST = os.getenv("DB_HOST", "mariadb")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "db")
DB_PASS = os.getenv("DB_PASS", "db")
DB_NAME = os.getenv("DB_NAME", "db")

def obtener_conexion():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    conn = obtener_conexion()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS asignaciones (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cosechadora_id VARCHAR(10) NOT NULL,
                camion_id VARCHAR(10) NOT NULL,
                fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                distancia FLOAT NOT NULL,
                estado VARCHAR(20) DEFAULT 'ASIGNADO'
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetria (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tipo_vehiculo VARCHAR(20) NOT NULL,
                vehiculo_id VARCHAR(10) NOT NULL,
                lat FLOAT NOT NULL,
                lon FLOAT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
        print("[DB] Tablas 'asignaciones' y 'telemetria' inicializadas correctamente.")
    finally:
        conn.close()

def guardar_telemetria(tipo_vehiculo, vehiculo_id, lat, lon):
    conn = obtener_conexion()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO telemetria (tipo_vehiculo, vehiculo_id, lat, lon) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (tipo_vehiculo, str(vehiculo_id), float(lat), float(lon)))
    finally:
        conn.close()

def registrar_mision(cosechadora_id, camion_id, distancia):
    conn = obtener_conexion()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO asignaciones (cosechadora_id, camion_id, distancia) VALUES (%s, %s, %s)"
            cursor.execute(sql, (str(cosechadora_id), str(camion_id), float(distancia)))
            print(f"[DB] Misión registrada: Cosechadora {cosechadora_id} -> Camión {camion_id} (Distancia: {distancia})")
    finally:
        conn.close()