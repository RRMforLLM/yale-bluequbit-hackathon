import pyzx as zx
from qiskit import QuantumCircuit, transpile
from qiskit.qasm2 import dumps
import glob
import os

def check_pyzx_collapse(qasm_path):
    print(f"\nAnalyzing: {os.path.basename(qasm_path)}")
    try:
        qc = QuantumCircuit.from_qasm_file(qasm_path)
        n = qc.num_qubits
        orig_gates = sum(qc.count_ops().values())
        
        basis = ['h', 'x', 'y', 'z', 's', 'sdg', 't', 'tdg', 'rx', 'rz', 'cx', 'cz']
        qc_t = transpile(qc, basis_gates=basis, optimization_level=3)
        transpiled_gates = sum(qc_t.count_ops().values())
        
        qasm_str = dumps(qc_t)
        c = zx.Circuit.from_qasm(qasm_str)
        g = c.to_graph()
        
        zx.full_reduce(g)
        
        # After full reduce, check the remaining vertices and edges
        print(f"  Qubits: {n}")
        print(f"  Original Gates:   {orig_gates}")
        print(f"  Transpiled Gates: {transpiled_gates}")
        print(f"  PyZX Vertices:    {g.num_vertices()} (Edges: {g.num_edges()})")
        
        if g.num_vertices() < transpiled_gates * 0.5:
            print("  --> MASSIVE COLLAPSE DETECTED!")
        else:
            print("  --> Rigid circuit (no massive algebraic collapse)")
            
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    files = sorted(glob.glob("yale/2026-bluequbit/challenge/*.qasm"))
    for f in files:
        name = os.path.basename(f)
        if name in ["P1_little_peak.qasm", "P2_small_bump.qasm", "P3_tiny_ripple.qasm", "P4_gentle_mound.qasm"]:
            continue # skip the ones we already did / failed
        check_pyzx_collapse(f)
