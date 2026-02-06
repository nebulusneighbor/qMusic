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
    [53, 57, 60],  # F Major (IV)
    [52, 55, 59],  # e minor (iii)
    [50, 53, 57]   # d minor (ii)
]
NOTES_PER_CHORD = 8  # 4 quarter notes per bar

# Ableton OSC Config
ABLETON_IP = "127.0.0.1"
ABLETON_PORT = 11000
TRACK_INDEX = 0      # Track to place the clip (0-indexed)
CLIP_INDEX = 0       # Clip slot to place the clip (0-indexed)
LENGTH = 4

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

def get_quantum_random_numbers(count, max_value):
    """
    Generates 'count' random numbers between 0 and max_value-1 using a quantum circuit.
    Uses rejection sampling to ensure uniform distribution if max_value is not a power of 2.
    """
    import math
    if max_value <= 0: return []
    if max_value == 1: return [0] * count
    
    num_qubits = math.ceil(math.log2(max_value))
    generated_numbers = []
    
    print(f"DEBUG: Generating {count} numbers in range [0, {max_value-1}] using {num_qubits} qubits...")
    
    sim = AerSimulator()
    
    while len(generated_numbers) < count:
        # Batch size: generate more than we need to account for rejections
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
def generate_and_sync():
    # Configuration for variable durations
    DURATIONS = [0.5, 1.0, 2.0]  # Eighth, Quarter, Half notes
    CHORD_DURATION = 4.0         # 1 bar per chord (assuming 4/4)
    
    num_chords_to_play = LENGTH  # Use the global LENGTH for number of bars/chords
    print(f"Selecting {num_chords_to_play} chords using Quantum Randomness...")
    
    # Select random chords
    chord_indices = get_quantum_random_numbers(num_chords_to_play, len(CHORDS))
    progression = [CHORDS[i] for i in chord_indices]
    
    # Estimate max notes needed to ensure we have enough random numbers
    # Max notes per chord = CHORD_DURATION / min(DURATIONS) = 8 / 0.5 = 16
    max_total_notes = int(num_chords_to_play * (CHORD_DURATION / min(DURATIONS))) + 10 # Buffer
    
    print(f"Generating quantum numbers for up to {max_total_notes} notes...")
    # We need random numbers for pitch (0-3) and duration (0-2)
    q_pitch_indices = get_quantum_random_numbers(max_total_notes, 4)
    q_duration_indices = get_quantum_random_numbers(max_total_notes, len(DURATIONS))
    
    notes_for_osc = []
    current_time = 0.0
    q_counter = 0
    
    print(f"Generating quantum melody (BPM: {TEMPO})...")
    
    for chord in progression:
        # Simple voicing: Triad + Octave root
        extended_chord = chord + [chord[0] + 12]
        
        chord_time = 0.0
        while chord_time < CHORD_DURATION:
            # Safety check if we run out of random numbers (unlikely with buffer)
            if q_counter >= len(q_pitch_indices):
                print("Warning: Ran out of pre-generated quantum numbers. Recycling.")
                q_counter = 0
            
            # Select Duration
            dur_index = q_duration_indices[q_counter]
            duration = DURATIONS[dur_index]
            
            # Check if duration fits in remaining chord time
            if chord_time + duration > CHORD_DURATION:
                # Try to fit the remainder or just clamp
                remaining = CHORD_DURATION - chord_time
                if remaining in DURATIONS:
                    duration = remaining
                else:
                    if remaining > 0:
                        duration = remaining
                    else:
                        break 
            
            # Select Pitch
            note_index = q_pitch_indices[q_counter]
            note_pitch = extended_chord[note_index]
            
            # Store for OSC: (pitch, start_time_beats, duration_beats, velocity)
            notes_for_osc.append((note_pitch, current_time, duration, 100))
            
            current_time += duration
            chord_time += duration
            q_counter += 1
            
    # --- ABLETON INTEGRATION ---
    try:
        print("Connecting to Ableton...")
        osc = AbletonOSCClient()
        
        # Calculate total length for clip (rounded up to nearest bar if needed)
        total_length_beats = current_time
              
        # Create Clip call to send actual length
        osc.client.send_message("/live/clip_slot/create_clip", [TRACK_INDEX, CLIP_INDEX, total_length_beats])
        
        # Small delay to ensure clip creation is processed
        time.sleep(0.2)
        
        # Send notes serially
        osc.add_notes(TRACK_INDEX, CLIP_INDEX, notes_for_osc)
        
        # Small delay before firing
        time.sleep(0.5)
        osc.fire_clip(TRACK_INDEX, CLIP_INDEX)
        
        print(f"Success! Melody sent ({total_length_beats} beats) and fired in Ableton.")
        
    except Exception as e:
        print(f"Could not connect to Ableton or send OSC: {e}")
        print("Ensure Ableton Live is running and AbletonOSC remote script is active.")

if __name__ == "__main__":
    generate_and_sync()