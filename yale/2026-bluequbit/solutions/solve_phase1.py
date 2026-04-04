import os
import json
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

# Yale phase 1 problems
problems = [
    {"name": "P1", "file": "../challenge/P1_little_peak.qasm", "qubits": 4},
    {"name": "P2", "file": "../challenge/P2_small_bump.qasm", "qubits": 12}, # Yale P2 is 12q
    {"name": "P3", "file": "../challenge/P3_tiny_ripple.qasm", "qubits": 30},
    {"name": "P4", "file": "../challenge/P4_gentle_mound.qasm", "qubits": 40},
    {"name": "P5", "file": "../challenge/P5_soft_rise.qasm", "qubits": 50},
]

sim_sv = AerSimulator(method='statevector')
# For MPS, we'll try a moderate bond dimension
sim_mps = AerSimulator(method='matrix_product_state', matrix_product_state_max_bond_dimension=128)

results = {}

def solve_phase1():
    out_file = "../results/phase1_results.json"
    
    for p in problems:
        qasm_path = os.path.join(os.path.dirname(__file__), p['file'])
        print(f"\n--- Solving {p['name']} ({p['qubits']} qubits) ---")
        
        if not os.path.exists(qasm_path):
            print(f"File not found: {qasm_path}")
            continue

        if p['qubits'] <= 24:
            sim = sim_sv
            print("Method: Statevector (Exact)")
        else:
            sim = sim_mps
            print("Method: MPS (BD=128)")
            
        try:
            qc = QuantumCircuit.from_qasm_file(qasm_path)
            
            # If the circuit doesn't have measurements, add them
            if len(qc.cregs) == 0:
                qc.measure_all()
            elif qc.num_clbits == 0:
                qc.measure_all()
                
            # Transpile mapping to the simulator
            qc_t = transpile(qc, sim)
            
            # Run with more shots for statistical significance on harder problems
            shots = 4096 if p['qubits'] > 30 else 1024
            print(f"Running {shots} shots...")
            job = sim.run(qc_t, shots=shots)
            counts = job.result().get_counts()
            
            winner = max(counts, key=counts.get)
            prob = counts[winner] / float(shots)
            
            print(f"Winner: {winner}")
            print(f"Prob:   {prob:.4f}")
            
            results[p['name']] = {
                "winner": winner,
                "probability": prob,
                "method": "statevector" if p['qubits'] <= 24 else "mps"
            }
            
        except Exception as e:
            print(f"Failed to solve {p['name']}: {e}")

    print("\n=== PHASE 1 RESULTS ===")
    for name, data in results.items():
        print(f"{name}: {data['winner']} (Prob: {data['probability']:.4f})")

    with open(out_file, "w") as f:
        json.dump(results, f, indent=4)
    print(f"\nSaved results to {out_file}")

if __name__ == '__main__':
    solve_phase1()