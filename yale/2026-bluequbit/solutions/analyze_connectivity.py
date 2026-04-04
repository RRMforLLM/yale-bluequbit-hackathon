import argparse
from qiskit import QuantumCircuit
import networkx as nx
import glob
import os

def analyze_connectivity(qasm_path):
    qc = QuantumCircuit.from_qasm_file(qasm_path)
    n = qc.num_qubits
    
    # Build interaction graph
    G = nx.Graph()
    G.add_nodes_from(range(n))
    
    for instruction in qc.data:
        qargs = instruction.qubits
        if len(qargs) == 2:
            u = qc.find_bit(qargs[0]).index
            v = qc.find_bit(qargs[1]).index
            G.add_edge(u, v)
        elif len(qargs) > 2:
            # Connect all to all in the gate
            indices = [qc.find_bit(q).index for q in qargs]
            for i in range(len(indices)):
                for j in range(i+1, len(indices)):
                    G.add_edge(indices[i], indices[j])
                    
    components = list(nx.connected_components(G))
    sizes = [len(c) for c in components]
    sizes.sort(reverse=True)
    
    name = os.path.basename(qasm_path)
    print(f"--- {name} ({n} qubits) ---")
    print(f"Number of connected components: {len(components)}")
    print(f"Component sizes: {sizes}")
    
    if len(components) > 1:
        print(f"YES! Factorable into {len(components)} subcircuits.")
    else:
        print("NO. Fully connected graph.")
    print("")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs="+", help="Paths to qasm files")
    args = parser.parse_args()
    
    files = args.files
    if not files:
        # Default to all challenges
        files = sorted(glob.glob("yale/2026-bluequbit/challenge/*.qasm"))
        
    for f in files:
        analyze_connectivity(f)
