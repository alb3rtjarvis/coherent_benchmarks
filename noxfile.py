import json
import os
import nox
import tempfile

BASE_DATA_DIR = os.path.abspath("./data")
RESULTS_DIR = os.path.abspath("./results")
BENCHMARK_PACKAGE = "benchmarks"
BENCHMARK_CASES = {
    "dg_ftle": {
        "description": "Double Gyre FTLE",
        "flow_type": "predefined",
        "flow_params": {
            "flow_data":{   
                "flow_str": "double_gyre",
                "grid_shape": (201, 101),
                'domain': ((0.0, 2.0), (0.0, 1.0)),
                "t0": 0.0,
                "T": 16.0,
                "dt0": 0.5
            },
            "iterates_per_run": 50, 
            "num_benchmark_runs": 3,
            "error_data": {
                #"path": os.path.join(BASE_DATA_DIR, "dg_ftle_true.npy"), "t0": 0.5, "T": 16.0
            }, # Make empty dict if not computing error (comment out above line)
            "pkg_specific_params": {"dynlab": {"num_threads": 8}} # num threads for your hardware
        }
    },
    "qge_ftle": {
        "description": "QGE FTLE",
        "flow_type": "data",
        "flow_params": {
            "flow_data":{   
                "flow_str": "qge",
                "vel_data_paths": {
                    "u": os.path.join(BASE_DATA_DIR, "qge_u.npy"),
                    "v": os.path.join(BASE_DATA_DIR, "qge_v.npy")
                },
                "domain": ((0.0, 1.0), (0.0, 1.0), (0.0, 2.0)),
                "t0": 0.0, 
                "T": 0.1, 
                "dt0": 0.01,
            },
            "iterates_per_run": 30, 
            "num_benchmark_runs": 3,
            "error_data": {
                #"path": os.path.join(BASE_DATA_DIR, "qge_ftle_true.npy"), "t0": 0.01, "T": 0.1
            }, # Make empty dict if not computing error (comment out above line)
            # lcstool wants (t, y, x) axes order, 'dimorder' tells how to permute data for this form
            "pkg_specific_params": {"lcstool": {"dimorder": [1, 3, 2]}}
        },
    }
}

PACKAGES_CONFIG = {
    "NumbaCS": {
        "runner_script": "runners/numbacs_runner.py",
        "conda_packages": [("numbacs", "conda-forge")], # (pkg, channel) tuples
        "python_version": "3.11",
        "venv_backend": "conda",
        "supported_cases": ["dg_ftle", "qge_ftle"]
    },
    "Dynlab": {
        "runner_script": "runners/dynlab_runner.py",
        "pip_packages": ["dynlab"],
        "python_version": "3.13",
        "venv_backend": "conda",
        "supported_cases": ["dg_ftle"]
    },
    "LCStool": {
        "runner_script": "runners/matlab_runner.py",
        "conda_packages": ["numpy"], # Need numpy to load data
        "python_version": "3.11", # Make sure your version of matlab supports this version of python
        "venv_backend": "conda",
        "matlab_scripts_map": {
            "predefined": "lcstool_dg_benchmark.m",
            "data": "lcstool_data_benchmark.m",
        },
        "matlab_scripts_dir": os.path.join("runners", "matlab_scripts"),
        "supported_cases": ["dg_ftle", "qge_ftle"]
    }
}

def ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)

for _pkg_name, _pkg_config in PACKAGES_CONFIG.items():
    for _case_id, _case_config in BENCHMARK_CASES.items():
        case_flow_type = _case_config["flow_type"]
        if _case_id not in _pkg_config["supported_cases"]:
            print(
                f"Skipping {_case_id} benchmark for {_pkg_name} since {_pkg_name} does not "
                "support this flow or flow type (or the benchmark has not yet been created)."
            )
            continue
        
        _session_name = f"bench-{_pkg_name.lower()}-{_case_id}"
        _py_version = _pkg_config["python_version"]
        _venv_backend = _pkg_config.get("venv_backend", "venv")
        
        @nox.session(name=_session_name, python=_py_version, venv_backend=_venv_backend)
        def benchmark_session(
                session: nox.Session, 
                pkg_name=_pkg_name, 
                pkg_config=_pkg_config, 
                case_id=_case_id,
                case_config=_case_config
        ):
            """Runs benchmark for specific package-case"""
            
            session.install("-e", ".")
            
            if session.venv_backend == "conda":
                if "conda_packages" in pkg_config:
                    for conda_pkg_spec in pkg_config["conda_packages"]:
                        if isinstance(conda_pkg_spec, tuple):
                            session.conda_install(conda_pkg_spec[0], channel=conda_pkg_spec[1])
                        else:
                            session.conda_install(conda_pkg_spec)
                if "pip_packages" in pkg_config and pkg_config["pip_packages"]: 
                    session.install(*pkg_config["pip_packages"])
            elif "dependencies" in pkg_config:
                session.install(*pkg_config["dependencies"])
            pkg_name_type = pkg_name
            pkg_name = pkg_name.lower()
            
            ensure_results_dir()
            output_filename = f"{pkg_name}_{case_id}_results.json"
            output_json_path_abs = os.path.join(RESULTS_DIR, output_filename)
            
            final_run_config = case_config["flow_params"].copy()
            final_run_config["output_json_path"] = output_json_path_abs
            
            final_run_config["metadata"] = {
                "package_name": pkg_name_type,
                "case_id": case_id,
                "case_description": case_config["description"],
                "case_flow_type": case_config["flow_type"]
            }
            
            if pkg_name in ["numbacs", "dynlab"]:
                run_config_json_str = json.dumps(final_run_config)
                session.run(
                    "python", pkg_config["runner_script"], "--run-config-json", run_config_json_str
                )
                
            elif pkg_name == 'lcstool':
                if not os.getenv("LCSTOOL_PATH"):
                    session.warn("LCSTOOL_PATH not set. Skipping MATLAB case.")
                    return
                
                flow_type = case_config["flow_type"]
                flow_name = final_run_config["flow_data"]["flow_str"]
                matlab_script_file = pkg_config["matlab_scripts_map"].get(flow_type)
                
                if not matlab_script_file:
                    session.warn(
                        f"No MATLAB script for {pkg_name} with "
                        f"flow '{flow_name}' ({flow_type}). Skipping."
                    )
                    return
                
                matlab_script_full_path = os.path.join(
                    pkg_config["matlab_scripts_dir"], matlab_script_file
                )
                
                # Write final_run_config to a temporary JSON file for MATLAB
                with tempfile.NamedTemporaryFile(
                        mode='w', 
                        suffix='.json', 
                        delete=False, 
                        dir=RESULTS_DIR, 
                        prefix=f"cfg_{pkg_name}_{case_id}_"
                    ) as tmp_f:
                    json.dump(final_run_config, tmp_f, indent=2)
                    temp_run_config_path_for_matlab = tmp_f.name
                
                session.log(f"  MATLAB run_config written to: {temp_run_config_path_for_matlab}")
                try:
                    session.run(
                        "python", pkg_config["runner_script"],
                        "--matlab-script", matlab_script_full_path,
                        "--run-config-json-path", temp_run_config_path_for_matlab
                    )
                finally:
                    if os.path.exists(temp_run_config_path_for_matlab):
                        os.remove(temp_run_config_path_for_matlab)
            else:
                session.warn(f"Runner logic not defined for package: {pkg_name}")
            