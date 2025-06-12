import argparse
import json
import os
import sys
import subprocess

def run_matlab_benchmark(
    matlab_script_path, 
    run_config_json_file_path,
    matlab_executable,
    expected_iter_time=200 
):
    """
    Executes the specified MATLAB benchmark script, passing it the path to a 
    JSON configuration file.

    Parameters
    ----------
    matlab_script_path : str
        path to matlab script containing the benchmark run.
    run_config_json_file_path : str
        Path to the JSON file containing the run_config 
    matlab_executable : str
        path to matlab executable, will default to 'matlab'.
        This works if matlab executable is on your path. See README for how to add to path.
    expected_iter_time : int or float, optional
        Expected time for one iterate, will change for different cases. The default is 200.

    Returns
    -------
    bool
        bool determining if matlab script executed successfully or not.

    """

    print(f"[Python MATLAB Runner] Preparing to run: {matlab_script_path}")
    print(f"  Run config JSON file: {run_config_json_file_path}")

    # Ensure paths are absolute for MATLAB
    script_dir_abs = os.path.abspath(os.path.dirname(matlab_script_path))
    script_name_no_ext = os.path.splitext(os.path.basename(matlab_script_path))[0]
    run_config_json_file_path_abs = os.path.abspath(run_config_json_file_path)

    # MATLAB command: cd to script's dir, then call the script as a function
    matlab_command = (
        f"cd('{script_dir_abs}'); "
        f"try; "
        # Call the MATLAB function (same name as script) with the path to the JSON config
        f"{script_name_no_ext}('{run_config_json_file_path_abs}'); " 
        f"catch e; fprintf(2, 'MATLAB Error in %s: %s\\n', '{script_name_no_ext}', getReport(e, 'extended', 'hyperlinks', 'off')); exit(1); "
        f"end; "
        f"exit(0);"
    )

    cmd = [matlab_executable, "-nodisplay", "-nosplash", "-batch", matlab_command]
    print(f"[Python MATLAB Runner] Executing: {' '.join(cmd)}")

    try:
        # Read iterates_per_run, num_benchmark_runs from the config file to estimate timeout
        with open(run_config_json_file_path_abs, 'r') as f_cfg:
            cfg_dict = json.load(f_cfg)
            iterates = cfg_dict['iterates_per_run']
            num_bench_runs = cfg_dict['num_benchmark_runs']

        timeout_seconds = expected_iter_time*iterates*num_bench_runs + 300 
        process = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=timeout_seconds
        )

        # Check process.returncode and output
        if process.returncode == 0:
            print(f"[Python MATLAB Runner] {script_name_no_ext} completed successfully.")
            if process.stdout: print(f"  MATLAB Stdout:\n{process.stdout.strip()}")
            # Output file creation is handled by MATLAB script based on output_json_path in config
        else:
            print(
                f"[Python MATLAB Runner] {script_name_no_ext} FAILED. "
                f"Return code: {process.returncode}", 
                file=sys.stderr
            )
            if process.stdout: 
                print(f"  MATLAB Stdout:\n{process.stdout.strip()}", file=sys.stderr)
            if process.stderr: 
                print(f"  MATLAB Stderr:\n{process.stderr.strip()}", file=sys.stderr)
            return False 
    
    except FileNotFoundError: # If MATLAB executable is not found
        print(
            f"ERROR: MATLAB executable '{matlab_executable}' not found. "
            "Ensure it's in PATH or provide full path.", 
            file=sys.stderr
        )
        return False
    except subprocess.TimeoutExpired as e:
        print(f"[Python MATLAB Runner] {script_name_no_ext} TIMED OUT.", file=sys.stderr)
        if e.stdout: 
            print(f"  MATLAB Stdout (partial):\n{e.stdout.strip()}", file=sys.stderr)
        if e.stderr: 
            print(f"  MATLAB Stderr (partial):\n{e.stderr.strip()}", file=sys.stderr)
        return False
    except Exception as e:
        print(
            f"[Python MATLAB Runner] Python error during MATLAB execution: "
            f"{type(e).__name__}: {e}", 
            file=sys.stderr
        )
        return False
            
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Python Runner for MATLAB Benchmark Scripts.")
    parser.add_argument(
        "--matlab-script", 
        required=True, 
        help="Path to the .m benchmark script to run."
    )
    parser.add_argument(
        "--run-config-json-path", 
        required=True,
        help="Path to the JSON file containing the run configuration for MATLAB."
    )
    parser.add_argument(
        "--matlab-executable", 
        default="matlab", 
        help="Path to MATLAB executable."
    )
    parser.add_argument(
        "--expected_iter_time", 
        default=200, 
        help="Expected time (s) to compute 1 iterate."
    )    
    
    args = parser.parse_args()

    if not os.path.isfile(args.matlab_script):
        print(f"Error: MATLAB script not found: {args.matlab_script}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(args.run_config_json_path):
        print(
            f"Error: MATLAB run configuration JSON not found: {args.run_config_json_path}", 
            file=sys.stderr
        )
        sys.exit(1)

    success = run_matlab_benchmark(
        args.matlab_script, 
        args.run_config_json_path, 
        args.matlab_executable
    )

    # The MATLAB script writes its own output JSON. This runner just signals success/failure.
    if success:
        print(f"[Python MATLAB Runner Main] Benchmark {args.matlab_script} has completed.")
    else:
        print(
            f"[Python MATLAB Runner Main] Benchmark {args.matlab_script} FAILED or had issues.", 
            file=sys.stderr
        )
        sys.exit(1)