import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from pythonosc import udp_client
import time

# --- 1. CONFIGURATION ---
TEMPO = 120
CHORDS = [
    [60, 64, 67],  # C Major (I)
    [55, 59, 62],  # G Major (V)
    [57, 60, 64],  # A Minor (vi)
    [53, 57, 60]   # F Major (IV)
]
NOTES_PER_CHORD = 4  # 4 quarter notes per bar

# Ableton OSC Config
ABLETON_IP = "127.0.0.1"
ABLETON_PORT = 11000
TRACK_INDEX = 0      # Track to place the clip (0-indexed)
CLIP_INDEX = 0       # Clip slot to place the clip (0-indexed)
LENGTH = 16

# --- 2. ABLETON OSC CLIENT ---
class AbletonOSCClient:
    def __init__(self, ip=ABLETON_IP, port=ABLETON_PORT):
        self.client = udp_client.SimpleUDPClient(ip, port)

    def create_clip(self, track_index, clip_index):
        """Creates a MIDI clip in the specified slot."""
        print(f"Creating clip at Track {track_index}, Slot {clip_index}...")
        self.client.send_message("/live/clip_slot/create_clip", [track_index, clip_index, LENGTH])

    def add_notes(self, track_index, clip_index, notes):
        """
        Sends notes to an Ableton clip serially.
        'notes' should be a list of (pitch, start_time, duration, velocity)
        """
        print(f"Adding {len(notes)} notes serially...")
        for note in notes:
            pitch, start, duration, velocity = note
            self.client.send_message("/live/clip/add/notes", [track_index, clip_index, pitch, start, duration, velocity, False])

    def fire_clip(self, track_index, clip_index):
        """Launches the clip."""
        print(f"Firing clip at Track {track_index}, Slot {clip_index}...")
        self.client.send_message("/live/clip_slot/fire", [track_index, clip_index])

# --- 3. QUANTUM ENGINE ---
def get_quantum_indices(num_notes):
    """
    Generates a list of random indices (0-3) using a Quantum Circuit.
    """
    qc = QuantumCircuit(2)
    qc.h([0, 1])
    qc.measure_all()
    
    sim = AerSimulator()
    job = sim.run(qc, shots=num_notes, memory=True)
    result = job.result()
    memory = result.get_memory()
    
    indices = [int(bitstring, 2) for bitstring in memory]
    return indices

# --- 4. MUSIC GENERATION & ABLETON SYNC ---
def generate_and_sync():
    # We need total random numbers = (chords) * (notes per chord)
    total_notes_needed = len(CHORDS) * NOTES_PER_CHORD
    quantum_randomness = get_quantum_indices(total_notes_needed)
    
    notes_for_osc = []
    current_time = 0.0
    q_counter = 0
    
    print(f"Generating quantum melody (BPM: {TEMPO})...")
    
    for chord in CHORDS:
        extended_chord = chord + [chord[0] + 12]
        
        for _ in range(NOTES_PER_CHORD):
            note_index = quantum_randomness[q_counter]
            note_pitch = extended_chord[note_index]
            
            # Store for OSC: (pitch, start_time_beats, duration_beats, velocity)
            notes_for_osc.append((note_pitch, current_time, 1.0, 100))
            
            current_time += 1.0
            q_counter += 1
            
    # --- ABLETON INTEGRATION ---
    try:
        print("Connecting to Ableton...")
        osc = AbletonOSCClient()
        
        # Create clip first
        osc.create_clip(TRACK_INDEX, CLIP_INDEX)
        
        # Small delay to ensure clip creation is processed
        time.sleep(0.2)
        
        # Send notes serially
        osc.add_notes(TRACK_INDEX, CLIP_INDEX, notes_for_osc)
        
        # Small delay before firing
        time.sleep(0.5)
        osc.fire_clip(TRACK_INDEX, CLIP_INDEX)
        
        print("Success! Melody sent and fired in Ableton.")
        
    except Exception as e:
        print(f"Could not connect to Ableton or send OSC: {e}")
        print("Ensure Ableton Live is running and AbletonOSC remote script is active.")

if __name__ == "__main__":
    generate_and_sync()