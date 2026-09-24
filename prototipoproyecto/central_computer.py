import paho.mqtt.client as mqtt
import ast

broker = "localhost"
port = 1883
topic = "central-computer"
topics = ["tractor", "truck"]
trucks = []
tractors = []

def on_connect(client, userdata, flags, reason_code):
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    for topic in topics:
        client.subscribe(topic)

def on_message(client, userdata, msg):
    msg.payload = ast.literal_eval(msg.payload.decode("utf-8"))
    print(msg.payload)
    if msg.topic == "truck":
        trucks.append(msg.payload)
    elif msg.topic == "tractor":
        if len(trucks) == 0:
            print("sent")
            client.publish(topic, f"Unfortunately, tractor with id {msg.payload[0]}, I must announce no trucks are available right now.")
        else:
            minimum = float("+inf")
            id = -1
            for truck in trucks:
                result = abs(msg.payload[1]-truck[1])
                if result < minimum:
                    minimum = result
                    id = truck[0] 
            client.publish(topic, f"Hey there, tractor {msg.payload[0]}, truck {id} will kindly come pick your load!")
client = mqtt.Client()
client.on_message = on_message
client.on_connect = on_connect
client.connect(broker, port)

client.loop_forever()