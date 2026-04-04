import argparse
import os
import json
import networkx as nx
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

def solve_factored(file_path, problem_name):
    print(f"\n--- Solving {problem_name} via Connectivity Factoring ---")
    qc = QuantumCircuit.from_qasm_file(file_path)
    n = qc.num_qubits

    # 1. Build the Interaction Graph to find components
    G = nx.Graph()
    G.add_nodes_from(range(n))
    
    for instruction in qc.data:
        qargs = instruction.qubits
        if len(qargs) == 2:
            u = qc.find_bit(qargs[0]).index
            v = qc.find_bit(qargs[1]).index
            G.add_edge(u, v)
        elif len(qargs) > 2:
            indices = [qc.find_bit(q).index for q in qargs]
            for i in range(len(indices)):
                for j in range(i+1, len(indices)):
                    G.add_edge(indices[i], indices[j])
                    
    components = list(nx.connected_components(G))
    components.sort(key=len, reverse=True)
    
    print(f"Qubits: {n}")
    print(f"Components found: {len(components)} -> Sizes: {[len(c) for c in components]}")
    
    if len(components) == 1:
        print("Circuit is fully connected. Cannot factorize.")
        return
        
    full_string = ["0"] * n
    
    # 2. Extract and Simulate Each Component Locally
    for idx, comp in enumerate(components):
        comp_qubits = sorted(list(comp))
        comp_size = len(comp_qubits)
        print(f"\n  [Subcircuit {idx+1}] Size: {comp_size} qubits")
        print(f"  Mapping: {comp_qubits}")
        
        if comp_size > 28:
            print("  WARNING: Subcircuit is larger than 28 qubits. Statevector may fail due to RAM limitations.")
            
        # Create an empty subcircuit with only the needed qubits
        sub_qc = QuantumCircuit(comp_size)
        qubit_map = {old_idx: new_idx for new_idx, old_idx in enumerate(comp_qubits)}
        
        # Pull operations that belong to this component
        for instruction in qc.data:
            qargs = instruction.qubits
            indices = [qc.find_bit(q).index for q in qargs]
            
            # If the gate operates entirely within this component
            if all(idx in comp for idx in indices):
                mapped_qargs = [sub_qc.qubits[qubit_map[i]] for i in indices]
                # Reconstruct instruction with new mapped qubits
                sub_qc.append(instruction.operation, mapped_qargs, instruction.clbits)

        sub_qc.measure_all()
        
        # Simulate subcircuit exactly using Statevector (Local RAM usage: ~32MB for 22 qubits)
        sim = AerSimulator(method='statevector')
        qc_t = transpile(sub_qc, sim)
        
        job = sim.run(qc_t, shots=1024)
        counts = job.result().get_counts()
        
        # Highest probability bitstring for this chunk
        winner = max(counts, key=counts.get)
        prob = counts[winner] / 1024.0
        
        print(f"  Winner for Subcircuit {idx+1}: {winner} (Prob: {prob:.4f})")
        
        # Qiskit outputs strings backwards (q_{n-1} ... q_0), so reverse it to plug into array properly
        # winner is length comp_size
        rev_winner = winner[::-1]
        
        for local_idx, global_idx in enumerate(comp_qubits):
            full_string[global_idx] = rev_winner[local_idx]

    # Put it all together
    final_bitstring = "".join(full_string[::-1])
    print(f"\n[!!!] FINAL ASSEMBLED {problem_name}: {final_bitstring}")
    
    os.makedirs("../results", exist_ok=True)
    out_file = f"../results/factored_{problem_name}.json"
    with open(out_file, "w") as f:
        json.dump({
            "problem": problem_name,
            "winner": final_bitstring,
            "method": "factoring+sv"
        }, f, indent=4)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="QASM file")
    parser.add_argument("--name", required=True, help="Challenge name")
    args = parser.parse_args()
    solve_factored(args.file, args.name)