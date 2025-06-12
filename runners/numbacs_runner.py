import argparse
import json
import os
import sys

# Try to import benchmark modules
try:
    from benchmarks.numbacs_benchmarks_ftle import (
        run_numbacs_predefined_ftle, run_numbacs_data_ftle
    )
except ImportError as e:
    print(f"ERROR: Could not import NumbaCS benchmark functions: {e}", file=sys.stderr)
    print(
        "Ensure 'benchmarks.numbacs_implementations' module exists and is importable.", 
        file=sys.stderr
    )
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="NumbaCS FTLE Benchmark Runner.")
    parser.add_argument(
        "--run-config-json", 
        required=True, 
        help="JSON string containing the full run configuration."
    )
    args = parser.parse_args()

    try:
        run_config = json.loads(args.run_config_json)

        # Extract common parameters expected by the implementation functions
        output_json_path = run_config['output_json_path']        
        flow_data_dict = run_config['flow_data']
        iterates_per_run = run_config['iterates_per_run']
        num_benchmark_runs = run_config['num_benchmark_runs']
        error_data_dict = run_config.get('error_data', {})
        metadata_dict = run_config.get('metadata', {})

        # Pre-processing: Load data from paths
        flow_type = run_config['metadata']['case_flow_type'] # Get flow_type from metadata

        if flow_type == 'data':
            if 'vel_data_paths' not in flow_data_dict:
                raise ValueError("NumbaCS 'data' flow type expects 'vel_data_paths' in flow_data.")

        if flow_type == 'predefined':
            run_numbacs_predefined_ftle(
                flow_data_dict, 
                output_json_path, 
                iterates_per_run, 
                num_benchmark_runs,
                error_data=error_data_dict,
                metadata=metadata_dict 
            )
        elif flow_type == 'data':
            run_numbacs_data_ftle(
                flow_data_dict,
                output_json_path,
                iterates_per_run,
                num_benchmark_runs,
                error_data=error_data_dict,
                metadata=metadata_dict
            )
        else:
            raise ValueError(f"Unsupported flow_type '{flow_type}' for NumbaCS runner.")

        print(
            f"[NumbaCS Runner] Benchmark '{run_config['metadata']['case_id']}' "
            "completed successfully."
          )

    except Exception as e:
        print(f"[NumbaCS Runner] Benchmark FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        # Try to get output_json_path from the original JSON string if parsing failed early
        output_path_for_error = "numbacs_error.json"
        try:
            # Attempt to parse JSON again just to get output path, if it fails, use default
            parsed_config_for_error_path = json.loads(args.run_config_json)
            output_path_for_error = (
                parsed_config_for_error_path.get('output_json_path', output_path_for_error)
            )
        except Exception:
            pass
        
        error_output = { 
            "package": "NumbaCS", 
            "error": f"{type(e).__name__}: {e}", 
            "run_config_json_str_received": args.run_config_json # Log what was received
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