# Author: ajarvis

import numpy as np
from dynlab.diagnostics import FTLE
from dynlab.flows import double_gyre, bickley_jet
import time
import json
import os
from benchmarks.utils import MAE

def run_dynlab_ftle(
        flow_data,
        output_json_path, 
        iterates_per_run, 
        num_benchmark_runs, 
        num_threads=8, 
        error_data={},
        metadata={}
):
    """
    Runs dynlab benchmark for double gyre or bickley_jet

    Parameters
    ----------
    flow_data : dict
        dict containing flow data with the following key-value pairs:
            flow_str: str, 
            domain: ((float, float), (float, float)), 
            grid_shape: (int, int), 
            t0: float, 
            T: float,
            dt0: float
    output_json_path : str
        path to output json file.
    iterates_per_run : int
        number of iterates per loop, should be at least 1.
    num_benchmark_runs : int
        number of benchmark runs to perform, should be at least 1.
    num_threads : int
        number of threads dynlab will use, default to 8 for comparison with NumbaCS
    error_data : dict
        dict containing path to data for error computation and parameters. The default is {}.
    metadata : dict
        dict containing metadata for specific package/case. The default is {}.        

    Returns
    -------
    None.

    """
    req_keys = {'flow_str', 'domain', 'grid_shape', 't0', 'T', 'dt0'}
    if not req_keys.issubset(flow_data.keys()):
        raise ValueError(f"The dict 'flow_data' must contain the following keys: {req_keys}")
    flow_str = flow_data['flow_str']
    if flow_str.lower() == 'double_gyre':
        f = double_gyre
    elif flow_str.lower() == 'bickley_jet':
        f = bickley_jet
    else:
        raise ValueError(
            "Currently, only supported flows for benchmarking are 'double_gyre "
            "and 'bickley_jet'. Dynlab supports many more flows but we "
            "do not benchmark them all here."
        )
    domain = flow_data['domain']
    nx, ny = flow_data['grid_shape']
    t0 = flow_data['t0']
    T = flow_data['T']
    dt0 = flow_data['dt0']
    package = metadata['package_name']
    case = metadata['case_description']
    print(f'--- {package} benchmark: {case} ---')
    print(f'Output JSON: {output_json_path}')
    print(f'Iterations per run: {iterates_per_run}')
    print(f'Number of benchmark runs: {num_benchmark_runs}')

    # Set up parameters
    x = np.linspace(domain[0][0], domain[0][1], nx)
    y = np.linspace(domain[1][0], domain[1][1], ny)
    
    results = {}
    results['parameters'] = {
        "iterates_per_run": iterates_per_run, 
        "num_benchmark_runs": num_benchmark_runs
    }
    timing_data = {}
    
    # First call and record warmup time
    print("Starting warm-up...")
    # Compute error from this warmup run if error_data supplied
    if error_data:
        ftle_true = error_data['true_data']
        t0_true = error_data['t0']
        wu_start = time.perf_counter()
        ftle_est = FTLE(num_threads=num_threads).compute(
            x, y, f, (t0_true, T + t0_true), edge_order=1, rtol=1e-6, atol=1e-8
        )
        warmup_time = time.perf_counter() - wu_start
        mae = MAE(ftle_true, ftle_est, edge=False)
        results['error'] = {'mae': mae, 'error_params': error_data['error_params']}
    else:
        wu_start = time.perf_counter()
        _ = FTLE(num_threads=num_threads).compute(
            x, y, f, (t0, T), edge_order=1, rtol=1e-6, atol=1e-8
        )
        warmup_time = time.perf_counter() - wu_start
    print(f"Warm-up completed, took {warmup_time:.5f} seconds.")
    
    # Benchmarks
    if num_benchmark_runs > 1:
        loop_times = np.zeros(num_benchmark_runs, np.float64)
        for i in range(num_benchmark_runs):
            print(f"Starting benchmark run {i+1} of {num_benchmark_runs}...")
            l_start = time.perf_counter()
            for k in range(iterates_per_run):
                _ = FTLE(num_threads=num_threads).compute(
                    x, y, f, (t0 + k*dt0, T + k*dt0), edge_order=1, rtol=1e-6, atol=1e-8
                ) 
            loop_time = time.perf_counter() - l_start
            print(
                f"Benchmark run {i+1} of {num_benchmark_runs} completed, "
                f"took {loop_time:.5f} seconds."
            )
            loop_times[i] = loop_time
        per_iter_times = loop_times/iterates_per_run
        timing_data['warmup_time'] = warmup_time
        timing_data['loop_times'] = loop_times.tolist()
        timing_data['per_iter_times'] = per_iter_times.tolist()
        timing_data['mean_loop_time'] = np.mean(loop_times)
        timing_data['mean_per_iter_time'] = np.mean(per_iter_times)
        timing_data['std_loop_time'] = np.std(loop_times)
        timing_data['std_per_iter_time'] = np.std(per_iter_times)
    elif num_benchmark_runs < 1:
        raise ValueError("num_benchmark_runs must be at least 1")
    else:
        print("Starting benchmark run 1 of 1...")
        l_start = time.perf_counter()
        for k in range(iterates_per_run):
            _ = FTLE(num_threads=num_threads).compute(
                x, y, f, (t0 + k*dt0, T + k*dt0), edge_order=1, rtol=1e-6, atol=1e-8
            ) 
        loop_time = time.perf_counter() - l_start
        print(
            f"Benchmark run 1 of 1 completed, "
            f"took {loop_time:.5f} seconds."
        )
        per_iter_time = loop_time/iterates_per_run
        timing_data['warmup_time'] = warmup_time
        timing_data['mean_loop_time'] = loop_time
        timing_data['mean_per_iter_time'] = per_iter_time
        timing_data['std_loop_time'] = 0.0
        timing_data['std_per_iter_time'] = 0.0
        
    results['timings'] = timing_data
    results['metadata'] = metadata
    
    # Write to JSON
    print(f"Saving results to: {output_json_path}")
    try:
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        with open(output_json_path, 'w') as f:
            json.dump(results, f, indent=2)
            print("Results saved.")
    except IOError as e:
        print(f"Error saving JSON: {e}")
        raise
    print(f"--- {package} benchmark complete ---")
