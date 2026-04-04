import argparse
import bluequbit
from qiskit import QuantumCircuit
import numpy as np
import time
import json
import os
from dotenv import load_dotenv

def solve_with_bluequbit(token, file_path, problem_name, mode="mps", shots=4096, bond_dim=None):
    bq = bluequbit.init(token)
    qc = QuantumCircuit.from_qasm_file(file_path)
    n = qc.num_qubits

    print(f"\n>>> Running {problem_name} on Bluequbit Cloud (Mode: {mode.upper()})")

    try:
        # Modes based on official docs:
        # 'cpu' (exact SV up to 34q, FREE)
        # 'gpu' (exact SV up to 35q, $3/hr)
        # 'mps.cpu' (MPS up to 96q, FREE limit)
        if mode == "mps":
            device = "mps.cpu"
        elif mode == "sv":
            device = "cpu" if n <= 34 else "gpu"
        else:
            device = mode  # allow explicit device passing
        
        # Options configurations based on past strategies  
        options = {}
        if mode.startswith("mps") and bond_dim:
            options["mps_bond_dimension"] = bond_dim
            
        print(f"Submitting {problem_name} to Bluequbit backend: {device}...")
        
        # If it doesn't have measurement, bluequbit API might need manual expect vs counts
        # We will use simple counts (run method with counts)
        if len(qc.cregs) == 0:
            qc.measure_all()
            
        job = bq.run(qc, device=device, shots=shots, job_name=f"Yale_{problem_name}", options=options)
        print(f"[SUBMITTED] Job ID: {job.job_id}")

        # Wait for outcome
        result = job.get_counts()
        winner = max(result, key=result.get)
        prob = result[winner] / float(shots)
        
        print(f"\n[!!!] FINAL {problem_name}: {winner}")
        print(f"      Probability:    {prob:.4f}")
        
        # Cache results locally
        os.makedirs(os.path.dirname(os.path.abspath(__file__)) + "/../results", exist_ok=True)
        out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"../results/cloud_{problem_name}.json")
        with open(out_file, "w") as f:
            json.dump({
                "problem": problem_name,
                "winner": winner,
                "probability": prob,
                "job_id": job.job_id,
                "mode": device
            }, f, indent=4)
        print(f"Results saved to {out_file}")

    except Exception as e:
        print(f"Error calling Bluequbit: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", help="Bluequbit API token (can also be set via BLUEQUBIT_TOKEN in .env)")
    parser.add_argument("--file", required=True, help="Path to qasm file")
    parser.add_argument("--name", required=True, help="Problem name (e.g. P3, P10)")
    parser.add_argument("--mode", default="sv", help="Type of GPU/MPS run (sv, mps, cpu, gpu, mps.cpu, mps.gpu, pauli-path.cpu)")
    parser.add_argument("--bond_dim", type=int, default=128, help="Bond dimension for MPS")
    
    args = parser.parse_args()
    
    load_dotenv()
    token = args.token or os.getenv("BLUEQUBIT_TOKEN")
    if not token:
        raise ValueError("Must provide Bluequbit API token via --token or BLUEQUBIT_TOKEN environment variable.")
        
    solve_with_bluequbit(token, args.file, args.name, args.mode, bond_dim=args.bond_dim)
