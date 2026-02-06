# Ableton OSC Config
ABLETON_IP = "127.0.0.1"
ABLETON_PORT = 11000

from pythonosc import udp_client
import time

client = udp_client.SimpleUDPClient(ABLETON_IP, ABLETON_PORT)
#verify message received
client.send_message("/live/test",[])

print("Sending test note to Ableton...")
# pitch, start, duration, velocity
client.send_message("/live/clip_slot/create_clip", [0,0,8])
client.send_message("/live/clip/add/notes", [0,0,60, 0.0, 1.0, 100,False])
client.send_message("/live/clip/add/notes", [0,0,62, 1.0, 1.0, 100,False])
client.send_message("/live/clip/add/notes", [0,0,64, 0.0, 1.0, 100,False])
client.send_message("/live/clip/add/notes", [0,0,65, 1.0, 1.0, 100,False])
client.send_message("/live/clip/add/notes", [0,0,67, 2.0, 1.0, 100,False])
client.send_message("/live/clip/add/notes", [0,0,69, 0.0, 1.0, 100,False])
client.send_message("/live/clip/add/notes", [0,0,71, 1.0, 1.0, 100,False])
client.send_message("/live/clip/add/notes", [0,0,72, 2.0, 1.0, 100,False])
client.send_message("/live/clip/add/notes", [0,0,69, 3.0, 1.0, 100,False])
client.send_message("/live/clip/add/notes", [0,0,71, 3.0, 1.0, 100,False])
client.send_message("/live/clip/add/notes", [0,0,72, 4.0, 1.0, 100,False])

time.sleep(0.5)
print("Firing clip...")
client.send_message("/live/clip_slot/fire", [0, 0])
