import argparse
import json
import os
import sys

# Try to import benchmark modules
try:
    from benchmarks.dynlab_benchmark_ftle import run_dynlab_ftle
except ImportError as e:
    print(f"ERROR: Could not import Dynlab benchmark function: {e}", file=sys.stderr)
    print(
        "Ensure 'benchmarks.dynlab_benchmark_ftle' module exists and is importable.", 
        file=sys.stderr
    )
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Dynlab FTLE Benchmark Runner.")
    parser.add_argument(
        "--run-config-json", 
        required=True, 
        help="JSON string containing the full run configuration."
    )
    args = parser.parse_args()

    try:
        run_config = json.loads(args.run_config_json)

        output_json_path = run_config['output_json_path']

        flow_data_dict = run_config['flow_data']
        iterates_per_run = run_config['iterates_per_run']
        num_benchmark_runs = run_config['num_benchmark_runs']
        error_data_dict = run_config.get('error_data', {})
        metadata_dict = run_config.get('metadata', {})
        
        # Dynlab has specific param num_threads
        pkg_specific_params = run_config.get('pkg_specific_params', {}).get('dynlab', {})
        num_threads = pkg_specific_params.get('num_threads', 8) # Default if not specified
        
        # Dynlab only supports predefined in this setup
        flow_type = run_config['metadata']['case_flow_type']
        if flow_type != 'predefined':
            raise ValueError(f"Dynlab runner received unsupported flow_type: {flow_type}")

        run_dynlab_ftle(
            flow_data_dict,
            output_json_path,
            iterates_per_run,
            num_benchmark_runs,
            num_threads=num_threads,
            error_data=error_data_dict,
            metadata=metadata_dict
        )
        print(
            f"[Dynlab Runner] Benchmark '{run_config['metadata']['case_id']}' "
            "completed successfully."
        )

    except Exception as e:
        print(f"[Dynlab Runner] Benchmark FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        output_path_for_error = "dynlab_error.json"
        try:
            parsed_config_for_error_path = json.loads(args.run_config_json)
            output_path_for_error = (
                parsed_config_for_error_path.get('output_json_path', output_path_for_error)
            )
        except Exception:
            pass
        
        error_output = { 
            "package": "Dynlab", 
            "error": f"{type(e).__name__}: {e}", 
            "run_config_json_str_received": args.run_config_json
        }
        try:
            if output_path_for_error:
                 output_dir = os.path.dirname(output_path_for_error)
                 if output_dir and not os.path.exists(output_dir): 
                     os.makedirs(output_dir)
                 with open(output_path_for_error, 'w') as f: 
                     json.dump(error_output, f, indent=2)
        except Exception: 
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()