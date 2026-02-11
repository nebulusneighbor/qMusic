import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from pythonosc import udp_client
import time
import keyboard

# --- 1. CONFIGURATION ---
TEMPO = 120
CHORDS = [
    [60, 64, 67],  # C Major (I)
    [55, 59, 62],  # G Major (V)
    [57, 60, 64],  # A Minor (vi)
    [53, 57, 60],  # F Major (IV)
    [52, 55, 59],  # e minor (iii)
    [50, 53, 57]   # d minor (ii)
]
NOTES_PER_CHORD = 16  # Fixed count per bar, but durations are randomized
CHORD_DURATION = 8.0  # Duration of one bar in beats
DURATIONS = [0, 0.5, 0.75, 1.0, 2.0] # Possible note lengths

# Ableton OSC Config
ABLETON_IP = "127.0.0.1"
ABLETON_PORT = 11000
INITIAL_TRACK_INDEX = 0      # Track to place the clip (0-indexed)
CLIP_INDEX = 0       # Clip slot to place the clip (0-indexed)
LENGTH = 4           # Number of bars (chords) per clip

# Global track counter
current_track_index = INITIAL_TRACK_INDEX

# --- 2. ABLETON OSC CLIENT ---
class AbletonOSCClient:
    def __init__(self, ip=ABLETON_IP, port=ABLETON_PORT):
        self.client = udp_client.SimpleUDPClient(ip, port)

    def create_clip(self, track_index, clip_index):
        """Creates a MIDI clip in the specified slot."""
        print(f"Creating clip at Track {track_index}, Slot {clip_index}...")
        self.client.send_message("/live/clip_slot/create_clip", [track_index, clip_index, LENGTH * CHORD_DURATION])

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

def get_quantum_random_numbers(count, max_value):
    """
    Generates 'count' random numbers between 0 and max_value-1 using a quantum circuit.
    """
    import math
    if max_value <= 0: return []
    if max_value == 1: return [0] * count
    
    num_qubits = math.ceil(math.log2(max_value))
    generated_numbers = []
    
    print(f"Generating {count} numbers in range [0, {max_value-1}] using {num_qubits} qubits...")
    
    sim = AerSimulator()
    
    while len(generated_numbers) < count:
        batch_size = (count - len(generated_numbers)) * 2 
        
        qc = QuantumCircuit(num_qubits)
        qc.h(range(num_qubits))
        qc.measure_all()
        
        job = sim.run(qc, shots=batch_size, memory=True)
        result = job.result()
        memory = result.get_memory()
        
        for bitstring in memory:
            val = int(bitstring, 2)
            if val < max_value:
                generated_numbers.append(val)
                if len(generated_numbers) == count:
                    break
                    
    return generated_numbers

# --- 4. MUSIC GENERATION & ABLETON SYNC ---
def generate_and_sync(track_index):
    # Setup progression
    print(f"Selecting {LENGTH} chords using Quantum Randomness...")
    chord_indices = get_quantum_random_numbers(LENGTH, len(CHORDS))
    progression = [CHORDS[i] for i in chord_indices]

    # Total notes needed
    total_notes_needed = LENGTH * NOTES_PER_CHORD
    
    # Poll quantum engine for pitches and durations
    print(f"Generating quantum pitches for {total_notes_needed} notes...")
    q_pitch_indices = get_quantum_random_numbers(total_notes_needed, 4)
    
    print(f"Generating quantum durations for {total_notes_needed} notes...")
    q_duration_indices = get_quantum_random_numbers(total_notes_needed, len(DURATIONS))
    
    notes_for_osc = []
    current_time = 0.0
    q_counter = 0
    
    print(f"Generating quantum melody (BPM: {TEMPO}, Density: {NOTES_PER_CHORD} notes/bar)...")
    
    for chord in progression:
        # Simple voicing: Triad + Octave root
        extended_chord = chord + [chord[0] + 12]
        
        for _ in range(NOTES_PER_CHORD):
            # Select Pitch
            note_index = q_pitch_indices[q_counter]
            note_pitch = extended_chord[note_index]
            
            # Select Duration
            dur_index = q_duration_indices[q_counter]
            note_duration = DURATIONS[dur_index]
            
            # Store for OSC: (pitch, start_time_beats, duration_beats, velocity)
            notes_for_osc.append((note_pitch, current_time, note_duration, 100))
            
            # Increment time
            current_time += note_duration
            q_counter += 1
            
    # --- ABLETON INTEGRATION ---
    try:
        print("Connecting to Ableton...")
        osc = AbletonOSCClient()
        
        # Create Clip
        osc.create_clip(track_index, CLIP_INDEX)
        
        # Small delay to ensure clip creation is processed
        time.sleep(0.2)
        
        # Send notes serially
        osc.add_notes(track_index, CLIP_INDEX, notes_for_osc)
        
        # Small delay before firing
        time.sleep(0.5)
        osc.fire_clip(track_index, CLIP_INDEX)
        
        print(f"Quantum Melody sent to Track {track_index} ({current_time} beats) and fired in Ableton.")
        
    except Exception as e:
        print(f"Could not connect to Ableton or send OSC: {e}")
        print("Ensure Ableton Live is running and AbletonOSC remote script is active.")

def on_space_pressed(event):
    global current_track_index
    print(f"\n--- Space Bar Pressed! Generating for Track {current_track_index} ---")
    generate_and_sync(current_track_index)
    current_track_index += 1
    print(f"Next track will be: {current_track_index}")
    print("Press SPACE to generate another track, or ESC to exit.")

if __name__ == "__main__":
    print("Quantum Music Generator Started!")
    print(f"Initial Track Index: {current_track_index}")
    print("Press SPACE to generate a new quantum melody for the next track.")
    print("Press ESC to exit.")
    
    # Hook the space bar
    keyboard.on_press_key("space", on_space_pressed)
    
    # Wait for the ESC key to exit the program
    keyboard.wait("esc")
    print("Exiting...")