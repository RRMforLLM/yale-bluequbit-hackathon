import argparse
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
import json
import os

def solve_approximate(file_path, problem_name, approx_degree=0.99):
    print(f"\n--- Running Approximate Transpilation on {problem_name} ---")
    
    try:
        qc = QuantumCircuit.from_qasm_file(file_path)
        n = qc.num_qubits
        original_ops = dict(qc.count_ops())
        original_total = sum(original_ops.values())
        print(f"Original circuit: {n} qubits, \nOps dict: {original_ops}, \nTotal gates: {original_total}")
        
        # If no measurements exist, add them
        if len(qc.cregs) == 0:
            qc.measure_all()
            
        print(f"Transpiling with approximation_degree={approx_degree}...")
        
        # The key: optimization_level 3 allows dropping identity noise
        # approximation_degree slightly allows unitary drift to cancel the gates
        sim = AerSimulator(method='matrix_product_state') if n > 24 else AerSimulator(method='statevector')
        
        # Adding basis gates to allow the transpiler to synthesize simple 1Q and CX gates nicely
        basis = ['u1', 'u2', 'u3', 'cx', 'id']
        qc_t = transpile(qc, sim, basis_gates=basis, optimization_level=3, approximation_degree=approx_degree)
        
        new_ops = dict(qc_t.count_ops())
        new_total = sum(new_ops.values())
        print(f"\nTranspiled circuit ops dict: {new_ops}, \nTotal gates: {new_total}")
        
        reduction = (original_total - new_total) / original_total * 100
        print(f"Gate count reduction: {reduction:.2f}%")
        
        # Attempt to run locally via MPS using standard bond dimensions
        options = {}
        if n > 24:
             # Bond dimension 128 is fine now since the gates and depth are massively shrunk
             options = {"matrix_product_state_max_bond_dimension": 128}
             print(f"Running on local MPS simulator...")
        else:
             print(f"Running on local StateVector simulator...")

        sim = AerSimulator(method='matrix_product_state', **options) if n > 24 else AerSimulator(method='statevector')
        
        job = sim.run(qc_t, shots=4096)
        counts = job.result().get_counts()
        
        winner = max(counts, key=counts.get)
        prob = counts[winner] / 4096.0
        
        print(f"\n[!!!] FINAL {problem_name}: {winner}")
        print(f"      Probability:    {prob:.4f}")
        
        # Cache results locally
        os.makedirs("../results", exist_ok=True)
        out_file = f"../results/approx_{problem_name}.json"
        
        with open(out_file, "w") as f:
             json.dump({
                 "problem": problem_name,
                 "winner": winner,
                 "probability": prob,
                 "method": "approx_transpile"
             }, f, indent=4)
             
    except Exception as e:
        print(f"Error during approx processing: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to qasm file")
    parser.add_argument("--name", required=True, help="Problem name (e.g. P6)")
    parser.add_argument("--approx", type=float, default=0.99, help="Approximation degree for Qiskit transpiler")
    args = parser.parse_args()
    
    solve_approximate(args.file, args.name, args.approx)