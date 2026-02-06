import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from midiutil import MIDIFile
from pythonosc import udp_client
import time

# --- 1. CONFIGURATION ---
FILENAME = "quantum_melody.mid"
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

# --- 2. ABLETON OSC CLIENT ---
class AbletonOSCClient:
    def __init__(self, ip=ABLETON_IP, port=ABLETON_PORT):
        self.client = udp_client.SimpleUDPClient(ip, port)

    def create_clip(self, track_index, clip_index, length_beats):
        """Creates a MIDI clip of specified length."""
        # AbletonOSC doesn't have a direct 'create_clip' but we can 
        # try to ensure the track exists or just clear/add notes to a slot.
        # Usually, adding notes will implicitly handle clip if the slot is valid.
        pass

    def add_notes(self, track_index, clip_index, notes):
        """
        Sends notes to an Ableton clip.
        'notes' should be a list of (pitch, start_time, duration, velocity, mute)
        """
        # Clear existing notes first (optional but recommended for fresh start)
        self.client.send_message(f"/live/clip/delete/notes", [track_index, clip_index])
        
        # AbletonOSC add/notes takes: track, clip, pitch, start, duration, velocity, mute
        # We can send them one by one or in batches if the API supports it.
        # Most AbletonOSC implementations expect: pitch, start, duration, velocity, mute per note
        for note in notes:
            pitch, start, duration, velocity = note
            self.client.send_message(f"/live/clip/add/notes", [track_index, clip_index, pitch, start, duration, velocity, 0])

    def fire_clip(self, track_index, clip_index):
        """Launches the clip."""
        print(f"Firing clip at Track {track_index}, Slot {clip_index}...")
        self.client.send_message("/live/play/clipslot", [track_index, clip_index])

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

# --- 4. MUSIC GENERATION ---
def generate_melody():
    # Setup MIDI File: 1 track, time 0
    midi = MIDIFile(1)
    midi.addTempo(0, 0, TEMPO)
    
    # We need total random numbers = (chords) * (notes per chord)
    total_notes_needed = len(CHORDS) * NOTES_PER_CHORD
    quantum_randomness = get_quantum_indices(total_notes_needed)
    
    current_time = 0
    q_counter = 0
    
    notes_for_osc = []
    
    print(f"Generating melody at {TEMPO} BPM...")
    
    for chord in CHORDS:
        extended_chord = chord + [chord[0] + 12]
        
        for _ in range(NOTES_PER_CHORD):
            note_index = quantum_randomness[q_counter]
            note_pitch = extended_chord[note_index]
            
            # Add note to MIDI (track, channel, pitch, time, duration, volume)
            midi.addNote(0, 0, note_pitch, current_time, 1, 100)
            
            # Store for OSC: (pitch, start_time_beats, duration_beats, velocity)
            notes_for_osc.append((note_pitch, float(current_time), 1.0, 100))
            
            current_time += 1
            q_counter += 1
            
    # Save to file
    with open(FILENAME, "wb") as output_file:
        midi.writeFile(output_file)
    print(f"Success! Saved to {FILENAME}")

    # --- 5. ABLETON INTEGRATION ---
    try:
        print("Connecting to Ableton...")
        osc = AbletonOSCClient()
        
        print(f"Sending {len(notes_for_osc)} notes to Ableton Track {TRACK_INDEX}, Slot {CLIP_INDEX}...")
        osc.add_notes(TRACK_INDEX, CLIP_INDEX, notes_for_osc)
        
        # Small delay to ensure notes are registered before firing
        time.sleep(0.5)
        osc.fire_clip(TRACK_INDEX, CLIP_INDEX)
        
    except Exception as e:
        print(f"Could not connect to Ableton or send OSC: {e}")
        print("Ensure Ableton Live is running and AbletonOSC remote script is active.")

if __name__ == "__main__":
    generate_melody()