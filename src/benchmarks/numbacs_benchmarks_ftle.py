from math import copysign
import numpy as np
from numbacs.flows import get_predefined_flow, get_interp_arrays_2D, get_flow_2D
from numbacs.integration import flowmap_grid_2D
from numbacs.diagnostics import ftle_grid_2D
import time
import json
import os
from benchmarks.utils import MAE

def run_numbacs_predefined_ftle(
        flow_data, 
        output_json_path, 
        iterates_per_run, 
        num_benchmark_runs, 
        error_data={},
        metadata={}
):
    """
    Runs numbacs benchmark for double gyre flow

    Parameters
    ----------
    flow_data : dict
        dict containing flow data with the following key-value pairs:
            flow_str: str, grid_shape: (int, int), t0: float, T: float, dt0: float 
    output_json_path : str
        path to output json file.
    iterates_per_run : int
        number of iterates per loop, should be at least 1.
    num_benchmark_runs : int
        number of benchmark runs to perform, should be at least 1.
    error_data : dict
        dict containing path to data for error computation and parameters. The default is {}.
    metadata : dict
        dict containing metadata for specific package/case. The default is {}.

    Returns
    -------
    None.

    """
    req_keys = {'flow_str', 'grid_shape', 't0', 'T', 'dt0'}
    if not req_keys.issubset(flow_data.keys()):
        raise ValueError(f"The dict 'flow_data' must contain the following keys: {req_keys}")
    flow_str = flow_data['flow_str']
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

    # Set up flow parameters
    funcptr, params, domain = get_predefined_flow(flow_str, int_direction = 1.0)
    x = np.linspace(domain[0][0], domain[0][1], nx)
    y = np.linspace(domain[1][0], domain[1][1], ny)
    dx = x[1] - x[0]
    dy = y[1] - y[0]
    
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
        flowmap = flowmap_grid_2D(funcptr, t0_true, T, x, y, params)
        ftle_est = ftle_grid_2D(flowmap, T, dx, dy)
        warmup_time = time.perf_counter() - wu_start
        mae = MAE(ftle_true, ftle_est, edge=False)
        results['error'] = {'mae': mae, 'error_params': error_data['error_params']}
    else:
        wu_start = time.perf_counter()
        flowmap = flowmap_grid_2D(funcptr, t0, T, x, y, params)
        _ = ftle_grid_2D(flowmap, T, dx, dy)
        warmup_time = time.perf_counter() - wu_start
    print(f"Warm-up completed, took {warmup_time:.5f} seconds.")
    
    # Run benchmarks
    if num_benchmark_runs > 1:
        loop_times = np.zeros(num_benchmark_runs, np.float64)
        for i in range(num_benchmark_runs):
            print(f"Starting benchmark run {i+1} of {num_benchmark_runs}...")
            l_start = time.perf_counter()
            for k in range(iterates_per_run):
                flowmap = flowmap_grid_2D(funcptr, t0 + k*dt0, T, x, y, params)
                _ = ftle_grid_2D(flowmap, T, dx, dy)
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
            flowmap = flowmap_grid_2D(funcptr, t0 + k*dt0, T, x, y, params)
            _ = ftle_grid_2D(flowmap, T, dx, dy)
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
    

def run_numbacs_data_ftle(
        flow_data, 
        output_json_path, 
        iterates_per_run, 
        num_benchmark_runs, 
        error_data={},
        metadata={}
):
    """
    Runs numbacs benchmark for double gyre flow

    Parameters
    ----------
    flow_data : dict
        dict containing flow data with the following key-value pairs:
            'flow_str': str,
            'vel_data_paths': {"u": "/path_to/u_data.npy", "v": "/path_to/v_data.npy"}
            'domain': ((float, float), (float, float), (float, float)) -- (tlims, xlims, ylims),
            't0': float, 
            'T': float,
            'dt0': float
    output_json_path : str
        path to output json file.
    iterates_per_run : int
        number of iterates per loop, should be at least 1.
    num_benchmark_runs : int
        number of benchmark runs to perform, should be at least 1.
    error_data : dict
        dict containing path to data for error computation and parameters. The default is {}.
    metadata : dict
        dict containing metadata for specific package/case. The default is {}.        

    Returns
    -------
    None.

    """
    req_keys = {'flow_str', 'vel_data_paths', 'domain', 't0', 'T', 'dt0'}
    if not req_keys.issubset(flow_data.keys()):
        raise ValueError(f"The dict 'flow_data' must contain the following keys: {req_keys}")
    u, v = (np.load(flow_data['vel_data_paths']['u']), np.load(flow_data['vel_data_paths']['v']))
    domain = flow_data['domain']
    nt, nx, ny = u.shape
    t0 = flow_data['t0']
    T = flow_data['T']
    dt0 = flow_data['dt0']
    package = metadata['package_name']
    case = metadata['case_description']
    print(f'--- {package} benchmark: {case} ---')
    print(f'Output JSON: {output_json_path}')
    print(f'Iterations per run: {iterates_per_run}')
    print(f'Number of benchmark runs: {num_benchmark_runs}')

    # Set up flow parameters
    t = np.linspace(domain[0][0], domain[0][1], nt)
    x = np.linspace(domain[1][0], domain[1][1], nx)
    y = np.linspace(domain[2][0], domain[2][1], ny)
    dx = x[1] - x[0]
    dy = y[1] - y[0]
    params = np.array([copysign(1, T)]) 
    
    results = {}
    results['parameters'] = {
        "iterates_per_run": iterates_per_run, 
        "num_benchmark_runs": num_benchmark_runs
    }
    timing_data = {}
    
    # Create interpolant
    print("Creating interpolant...")
    grid_vel, C_eval_u, C_eval_v = get_interp_arrays_2D(t, x, y, u, v)
    
    # Retrieve function pointer
    funcptr = get_flow_2D(grid_vel, C_eval_u, C_eval_v)
    print("Interpolant created.")
    
    
    # First call and record warmup time
    print("Starting warm-up...")
    # Compute error from this warmup run if error_data supplied
    if error_data:
        ftle_true = error_data['true_data']
        t0_true = error_data['t0']
        wu_start = time.perf_counter()
        flowmap = flowmap_grid_2D(funcptr, t0_true, T, x, y, params)
        ftle_est = ftle_grid_2D(flowmap, T, dx, dy)
        warmup_time = time.perf_counter() - wu_start
        mae = MAE(ftle_true, ftle_est, edge=False)
        results['error'] = {'mae': mae, 'error_params': error_data['error_params']}
    else:
        wu_start = time.perf_counter()
        flowmap = flowmap_grid_2D(funcptr, t0, T, x, y, params)
        _ = ftle_grid_2D(flowmap, T, dx, dy)
        warmup_time = time.perf_counter() - wu_start
    print(f"Warm-up completed, took {warmup_time:.5f} seconds.")
    
    # Benchmarks
    if num_benchmark_runs > 1:
        loop_times = np.zeros(num_benchmark_runs, np.float64)
        for i in range(num_benchmark_runs):
            print(f"Starting benchmark run {i+1} of {num_benchmark_runs}...")
            l_start = time.perf_counter()
            for k in range(iterates_per_run):
                flowmap = flowmap_grid_2D(funcptr, t0 + k*dt0, T, x, y, params)
                _ = ftle_grid_2D(flowmap, T, dx, dy)
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
            flowmap = flowmap_grid_2D(funcptr, t0 + k*dt0, T, x, y, params)
            _ = ftle_grid_2D(flowmap, T, dx, dy)
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