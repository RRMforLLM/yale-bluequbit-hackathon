import argparse
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
import pyzx as zx
import sys
import json
import os

def pyzx_simplify_and_solve(qasm_path, problem_name):
    print(f"\n--- Running PyZX reduction on {problem_name} ---")
    try:
        qc = QuantumCircuit.from_qasm_file(qasm_path)
        print(f"Original circuit: {qc.num_qubits} qubits, {sum(qc.count_ops().values())} gates")
        
        # PyZX parses standard Clifford+T + phase gates well. 
        # Transpile Qiskit's u3/cz etc. into PyZX-friendly basis
        basis = ['h', 'x', 'y', 'z', 's', 'sdg', 't', 'tdg', 'rx', 'rz', 'cx', 'cz']
        qc_t = transpile(qc, basis_gates=basis, optimization_level=3)
        print(f"Transpiled to PyZX basis: {sum(qc_t.count_ops().values())} gates")
        
        # Export to QASM and load into PyZX
        from qiskit.qasm2 import dumps
        qasm_str = dumps(qc_t)
        
        # Load string into PyZX
        import pyzx as zx
        c = zx.Circuit.from_qasm(qasm_str)
        
        # Convert to ZX-graph and apply full algebraic reduction
        g = c.to_graph()
        zx.full_reduce(g)
        
        print(f"ZX Graph after full_reduce: {g.num_vertices()} vertices, {g.num_edges()} edges")
        
        # If the graph is heavily reduced, we can extract it back to a circuit
        c_opt = zx.extract_circuit(g)
        optimized_qasm = c_opt.to_qasm()
        
        qc_opt = QuantumCircuit.from_qasm_str(optimized_qasm)
        print(f"Extracted optimized circuit gates: {sum(qc_opt.count_ops().values())}")
        
        # If it's small enough, simulate it locally!
        # Re-add measurements
        qc_opt.measure_all()
        
        # Simulate with statevector locally
        sim = AerSimulator(method='statevector')
        job = sim.run(transpile(qc_opt, sim), shots=1024)
        counts = job.result().get_counts()
        
        winner = max(counts, key=counts.get)
        prob = counts[winner] / 1024.0
        
        print(f"\n[!!!] FINAL {problem_name}: {winner}")
        print(f"      Probability:    {prob:.4f}")
        
        os.makedirs("../results", exist_ok=True)
        out_file = f"../results/pyzx_{problem_name}.json"
        with open(out_file, "w") as f:
            json.dump({
                "problem": problem_name,
                "winner": winner,
                "probability": prob,
                "method": "pyzx+sv"
            }, f, indent=4)
            
    except Exception as e:
        print(f"Error during PyZX simplification: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to qasm file")
    parser.add_argument("--name", required=True, help="Name of the problem")
    args = parser.parse_args()
    
    pyzx_simplify_and_solve(args.file, args.name)
