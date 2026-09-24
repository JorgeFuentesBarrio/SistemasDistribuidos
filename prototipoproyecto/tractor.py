import paho.mqtt.client as mqtt

broker = "localhost"
port = 1883
topic = "tractor"

def on_connect(client, userdata, flags, reason_code):
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("central-computer")
    client.publish(topic, "(1,100)")

def on_message(client, userdata, msg):
    print(str(msg.payload))

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(broker, port)
client.loop_forever()