import os
import sys
import argparse
import subprocess
from dotenv import load_dotenv

SOLUTIONS_DIR = os.path.dirname(os.path.abspath(__file__))
CHALLENGE_DIR = os.path.join(SOLUTIONS_DIR, "../challenge")

# Known exact solution mappings based on our diagnostics
STRATEGIES = {
    "P1_little_peak":   {"method": "local_sv", "note": "4q trivial"},
    "P2_small_bump":    {"method": "local_sv", "note": "12q exact statevector"},
    "P3_tiny_ripple":   {"method": "cloud_sv", "note": "30q exact via BlueQubit FREE cpu"},
    "P4_gentle_mound":  {"method": "cloud_pps", "note": "40q high density -> pauli-path.gpu ($)"}, # Needs credits
    "P5_soft_rise":     {"method": "cloud_pps", "note": "50q -> pauli-path.gpu ($)"},
    "P6_low_hill":      {"method": "cloud_pps", "note": "60q -> pauli-path.gpu ($)"},
    "P7_rolling_ridge": {"method": "factor_sv", "note": "42q -> Factored into 22q + 20q EXACT!"},
    "P8_bold_peak":     {"method": "cloud_pps", "note": "58q -> pauli-path.gpu ($)"},
    "P9_grand_summit":  {"method": "cloud_pps", "note": "69q -> pauli-path.gpu ($)"},
    "P10_eternal_mountain": {"method": "cloud_pps", "note": "56q -> pauli-path.gpu ($)"}
}

def run_command(args):
    cmd = [sys.executable] + args
    print(f"\n{'='*60}")
    print(f"Executing: {' '.join(cmd[1:])}")
    print(f"{'='*60}")
    subprocess.run(cmd)

def main():
    parser = argparse.ArgumentParser(description="Unified Yale 2026 Bluequbit Solver")
    parser.add_argument("--problem", help="Execute specific problem (e.g. P1, P7, or 'all')", default="all")
    parser.add_argument("--use-credits", action="store_true", help="Allow running $20 GPU backends for hard circuits")
    args = parser.parse_args()

    load_dotenv()
    if not os.getenv("BLUEQUBIT_TOKEN"):
        print("WARNING: BLUEQUBIT_TOKEN missing from .env. Cloud-dependent solves will fail.")

    qasm_files = sorted(os.listdir(CHALLENGE_DIR))
    
    for f in qasm_files:
        if not f.endswith(".qasm"):
            continue
            
        problem_prefix = f.split("_")[0] # e.g. "P1"
        if args.problem != "all" and problem_prefix.upper() != args.problem.upper():
            continue
            
        base_name = f.replace(".qasm", "")
        strategy = STRATEGIES.get(base_name, {"method": "unknown", "note": "Unknown"})
        file_path = os.path.join(CHALLENGE_DIR, f)
        
        print(f"\n[{problem_prefix}] Strategy mapped: {strategy['method']} ({strategy['note']})")
        
        if strategy["method"] == "local_sv":
            # For P1, P2 we can reuse solve_phase1.py but adapting it to run single files would be better.
            # Instead, we just use solve_cloud.py with 'cpu' locally? No, solve_cloud reaches API.
            run_command([os.path.join(SOLUTIONS_DIR, "solve_approximate.py"), 
                         "--file", file_path, "--name", problem_prefix])
                         
        elif strategy["method"] == "cloud_sv":
            run_command([os.path.join(SOLUTIONS_DIR, "solve_cloud.py"), 
                         "--file", file_path, "--name", problem_prefix, "--mode", "sv"])

        elif strategy["method"] == "factor_sv":
            run_command([os.path.join(SOLUTIONS_DIR, "solve_factored.py"), 
                         "--file", file_path, "--name", problem_prefix])
                         
        elif strategy["method"] == "cloud_pps":
            if not args.use_credits:
                print(f"  -> Skipping {problem_prefix} because it requires GPU credits (use --use-credits to authorize).")
            else:
                # Dispatching to the GPU pauli-path
                # You'd use solve_cloud.py but requesting the pauli-path.gpu or mps.gpu
                run_command([os.path.join(SOLUTIONS_DIR, "solve_cloud.py"), 
                             "--file", file_path, "--name", problem_prefix, "--mode", "pauli-path.gpu"])

if __name__ == "__main__":
    main()