# Coordinacion Autonoma de Cosechadoras y Flotas de Transporte en Entornos Agricolas

Simulacion distribuida para coordinar la descarga de cereal entre cosechadoras y camiones en el campo. 

## Como funciona

1. Cosechadoras: Van llenando su tolva poco a poco. Al llegar al 80% piden vaciado por MQTT y se quedan esperando.
2. Central: Recibe la peticion, mira el camión libre mas cercano y le manda la orden. Si no hay camiones libres, mete la cosechadora en una cola de espera. Ademas, guarda las coordenadas y las misiones en la base de datos.
3. Camiones: Van hacia las cosechadoras asignadas, llevan el grano al silo central y esperan otro viaje.
4. CockroachDB: Guarda el historico en un cluster distribuido de 3 nodos.
5. Node-RED: Se suscribe al broker y muestra las posiciones y el estado de los vehículos en un mapa interactivo.

## Como arrancar el proyecto

**Estos comandos se deben ejecutar en la carpeta raiz del proyecto**, es decir, donde podemos encontrar el archivo `docker-compose.yml`.

1. Construir las imágenes

`docker compose build --no-cache`

2. Levantar el sistema

`docker compose up`

3. Parar el sistema

`docker compose down -v`

## Visualización

- Mapa `http://localhost:1880/worldmap`
