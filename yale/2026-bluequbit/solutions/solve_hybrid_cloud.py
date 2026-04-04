import argparse
import bluequbit
from qiskit import QuantumCircuit, transpile
import json
import os
from dotenv import load_dotenv

def solve_approximate_cloud(token, file_path, problem_name, mode="mps.cpu", approx_degree=0.99, shots=4096):
    print(f"\n--- Running Hybrid (Local Transpile -> Cloud Run) on {problem_name} ---")
    
    try:
        # 1. Load circuit locally
        qc = QuantumCircuit.from_qasm_file(file_path)
        n = qc.num_qubits
        
        original_ops = dict(qc.count_ops())
        original_total = sum(original_ops.values())
        print(f"Original circuit: {n} qubits, Total gates: {original_total}")
        
        if len(qc.cregs) == 0:
            qc.measure_all()
            
        print(f"Transpiling locally with approximation_degree={approx_degree}... (Very low RAM usage)")
        
        # 2. Transpile locally (shrinks gate count without simulating)
        # Add a placeholder backend or just basis gates to let Qiskit simplify
        basis = ['u1', 'u2', 'u3', 'cx', 'id', 'rz', 'sx', 'x']
        qc_t = transpile(qc, basis_gates=basis, optimization_level=3, approximation_degree=approx_degree)
        
        new_ops = dict(qc_t.count_ops())
        new_total = sum(new_ops.values())
        print(f"Transpiled circuit Total gates: {new_total}")
        
        reduction = (original_total - new_total) / original_total * 100
        print(f"Gate count reduction: {reduction:.2f}%")
        
        # 3. Send the much-smaller circuit to Bluequbit completely bypassing local 8GB RAM limits!
        bq = bluequbit.init(token)
        print(f"Submitting heavily reduced circuit to Bluequbit backend: {mode}...")
        
        job = bq.run(qc_t, device=mode, shots=shots, job_name=f"Yale_Approx_{problem_name}")
        print(f"[SUBMITTED] Job ID: {job.job_id}")

        result = job.get_counts()
        winner = max(result, key=result.get)
        prob = result[winner] / float(shots)
        
        print(f"\n[!!!] FINAL {problem_name}: {winner}")
        print(f"      Probability:    {prob:.4f}")
        
        # Cache results
        os.makedirs(os.path.dirname(os.path.abspath(__file__)) + "/../results", exist_ok=True)
        out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"../results/hybrid_cloud_{problem_name}.json")
        with open(out_file, "w") as f:
            json.dump({
                "problem": problem_name,
                "winner": winner,
                "probability": prob,
                "job_id": job.job_id,
                "method": f"approx_{approx_degree} + {mode}"
            }, f, indent=4)
            
    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to qasm file")
    parser.add_argument("--name", required=True, help="Problem name (e.g. P4)")
    parser.add_argument("--approx", type=float, default=0.99, help="Approximation degree")
    parser.add_argument("--mode", default="mps.cpu", help="Bluequbit backend")
    args = parser.parse_args()
    
    load_dotenv()
    token = os.getenv("BLUEQUBIT_TOKEN")
    
    solve_approximate_cloud(token, args.file, args.name, args.mode, args.approx)
