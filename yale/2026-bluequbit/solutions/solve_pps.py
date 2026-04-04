import argparse
import bluequbit
from qiskit import QuantumCircuit
import numpy as np
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

def get_pauli_str(i, n):
    return "I" * i + "Z" + "I" * (n - 1 - i)

def solve_qubit(bq, name, qc, i, n, threshold):
    pauli_str = get_pauli_str(i, n)
    pauli_sum = [(pauli_str, 1.0)]
    job_name = f"Yale_{name}_q{i}"
    
    try:
        job = bq.run(qc, device="pauli-path", pauli_sum=pauli_sum, job_name=job_name, 
                     options={
                         'pauli_path_truncation_threshold': threshold,
                         'pauli_path_circuit_transpilation_level': 1
                     })
        val = job.expectation_value
        bit = '1' if val < 0 else '0'
        return i, bit, val, None
    except Exception as e:
        return i, None, None, str(e)

def run_pps_parallel(token, file_path, name, threshold=1e-4, workers=15):
    bq = bluequbit.init(token)
    qc = QuantumCircuit.from_qasm_file(file_path)
    
    if len(qc.cregs) > 0:
        qc.remove_final_measurements()
        
    n = qc.num_qubits
    bitstring = [None] * n
    
    out_dir = os.path.join(os.path.dirname(__file__), "../results")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"pps_{name}.json")
    
    results_cache = {}
    if os.path.exists(out_file):
        with open(out_file, "r") as f:
            results_cache = json.load(f)
            for str_k, v in results_cache.items():
                if str_k.isdigit():
                    bitstring[int(str_k)] = v['bit']
                    
    print(f"\n>>> Running PPS Attack on {name} ({n} qubits, threshold={threshold})")
    
    def process_qubit(i):
        if str(i) in results_cache:
            return i, results_cache[str(i)]['bit'], results_cache[str(i)]['val'], None
        return solve_qubit(bq, name, qc, i, n, threshold)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_qubit, i): i for i in range(n)}
        
        for future in as_completed(futures):
            idx, bit, val, err = future.result()
            if bit is not None:
                bitstring[idx] = bit
                results_cache[str(idx)] = {'bit': bit, 'val': val}
                with open(out_file, "w") as f:
                    json.dump(results_cache, f, indent=4)
                if err is None and str(idx) not in results_cache:
                     print(f"  [{name}] Qubit {idx} DONE: {bit} (E = {val:.4f})")
                elif err is None:
                     print(f"  [{name}] Qubit {idx} DONE: {bit} (E = {val:.4f})")
            else:
                print(f"  [{name}] Qubit {idx} FAILED: {err}")

    if all(b is not None for b in bitstring):
        final_str = "".join(bitstring[::-1])  # Qiskit endianness matching
        print(f"\n[!!!] FINAL {name}: {final_str}")
        return final_str
    else:
        print("\nSome qubits failed to compute.")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to qasm file")
    parser.add_argument("--name", required=True, help="Problem name (e.g. P4)")
    args = parser.parse_args()
    
    load_dotenv()
    token = os.getenv("BLUEQUBIT_TOKEN")
    
    run_pps_parallel(token, args.file, args.name)