# Coherent Benchmarks

This repository is meant to benchmark various coherent structure pacakges, with a focus on how the performance of these packages compare with [`NumbaCS`](https://github.com/alb3rtjarvis/numbacs). 
Currently, we compare `NumbaCS` with [`Dynlab`](https://github.com/hokiepete/dynlab) and [`LCStool`](https://github.com/haller-group/LCStool). In the future, we aim to provide benchmarks for a wider variety of cases and functionality, and with other similar packages 
(see [Similar software](https://github.com/alb3rtjarvis/numbacs?tab=readme-ov-file#similar-software))

The primary goal of this repository is to provide easily accessible benchmark results. For details on how these benchmarks are run or to contribute, see the "Running and Updating Benchmarks" section below. For all other users, just view the "Benchmark Results" section below.

## Benchmark Results

Hardware: Intel(R) Core(TM) i7-3770K CPU @ 3.50GHz, Cores = 4, Threads = 8

<!-- BENCHMARK_RESULTS_START -->

### Double Gyre FTLE (Iter/Run: 50, Num Runs: 3)

| Package   |   Mean /Iter (s) |   Std /Iter (s) | Speedup (vs NumbaCS)   |
|:----------|-----------------:|----------------:|:-----------------------|
| NumbaCS   |           0.1795 |          0.0012 | 1.00                   |
| Dynlab    |          21.1612 |          0.2593 | (117.88)⁻¹             |
| LCStool   |           4.5336 |          0.014  | (25.26)⁻¹              |

---

### QGE FTLE (Iter/Run: 30, Num Runs: 3)

| Package   |   Mean /Iter (s) |   Std /Iter (s) | Speedup (vs NumbaCS)   |
|:----------|-----------------:|----------------:|:-----------------------|
| NumbaCS   |           2.5362 |          0.0169 | 1.00                   |
| LCStool   |         105.18   |          0.2927 | (41.47)⁻¹              |

<!-- BENCHMARK_RESULTS_END -->

## Running and Updating Benchmarks

This section is for users who wish to run the benchmarks themselves, for example, to test on their own hardware, add new packages/cases, or to update results.

### Prerequisites

-  **Conda:** Required for managing environments. See [Miniforge](https://github.com/conda-forge/miniforge), [Mabma/Micromamba](https://github.com/mamba-org/mamba), or [Miniconda](https://docs.conda.io/en/latest/miniconda.html) for installation instructions.
-  **Git:** For cloning the repository.

### Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your_repository_url>
    cd /path/to/your/coherent_benchmarks
    ```

2.  **Create and Activate the Benchmark Environment:**
    This environment is used to run `nox`, which manages individual benchmark environments.
    ```bash
    conda env create -f environment-bench.yml
    conda activate coherent-bench
    ```

### Running Benchmarks with `nox`

We use [`nox`](https://nox.thea.codes/en/stable/) to automate the creation of isolated environments and execution for each benchmark. Assuming you are in the `coherent_benchmarks` directory:

-   **List available benchmark sessions:**
    ```bash
    nox -l
    ```
-   **Run all defined benchmark sessions:**
    ```bash
    nox
    ```
-   **Run a specific session:** (e.g., `bench-numbacs-dg_ftle` - find exact names from `nox -l`)
    ```bash
    nox -s bench-numbacs-dg_ftle
    ```
-   **Run all sessions for a specific package or keyword:**
    ```bash
    nox -k numbacs  # Runs all sessions containing "numbacs"
    ```
-  **(Optional) Delete all `nox` envs**: `nox` will  generate environments for each benchmark run. To delete them, simply delete the `.nox` directory from the `coherent_benchmark` directory
   ```bash
  rm -rf .nox
  ```

### Generating Tables and Updating the README Results Tables

After running benchmarks and generating new JSON results:

1.  Ensure the `coherent-bench` environment is active.
2.  Run the `readme_updater.py` script to update the tables in this `README.md`:
	-  To generate tables **and** update `README.md`:
	
    ```bash
    python src/readme_updater.py
    ```

	-  To generate tables **without** updating `README.md`:
	
    ```bash
    python src/readme_updater.py tables-only
    ```
    
---

### MATLAB-Specific Considerations (For LCStool Benchmarks)

If you intend to run or develop benchmarks involving MATLAB (LCStool):

1.  **MATLAB Installation:** A licensed version of MATLAB must be installed.
2.  **MATLAB Executable in System PATH:**
    The directory containing the MATLAB executable (e.g., `R20XXx/bin`) needs to be on your system's `PATH` so that `matlab` can be called from the command line.
    -   *Windows Example:* `C:\Program Files\MATLAB\R2023b\bin`
    -   *Linux Example:* `/usr/local/MATLAB/R2023b/bin`
    -   *macOS Example:* `/Applications/MATLAB_R2023b.app/bin`
    
    (Refer to your operating system's documentation for adding directories to the PATH).
3.  **LCStool Codebase and LCSTOOL_PATH:**
	We **do not** provide the actual source code for any benchmark packages. For MATLAB packages, it is assumed you already have the source code on your machine (Python packages will be installed by `nox` using either `conda` or `pip`). If you do not have the source code on your machine, git clone the LCStool repository [https://github.com/haller-group/LCStool](https://github.com/haller-group/LCStool) to a directory of your choice. Following that, set the `LCSTOOL_PATH` environment variable to the root of this directory.
    -   Linux/macOS: `export LCSTOOL_PATH="/path/to/your/LCStool"`
    -   Windows PowerShell: `$env:LCSTOOL_PATH = "C:\path\to\your\LCStool"`
4.  **Python for MATLAB:**
	To avoid having redundunt copies of data for numerical flows for both Python and MATLAB, all data is stored as `.npy` files and we use MATLAB's Python interface to load the data for the MATLAB benchmarks. MATLAB's Python interface requires a specific Python version with NumPy installed. This Python version must be compatible with your MATLAB version.
    -   Identify a compatible Python version (see [compatibility](https://www.mathworks.com/support/requirements/python-compatibility.html)).
    -   In `noxfile.py`, for the `LCStool` key in `PACKAGES_CONFIG`, set `python_version` to the appropriate compatible version.

### General Considerations

- It is possible `nox` is degrading performance slightly. `nox` was not designed for benchmarking, it was designed to automate Python testing in different environments but we use it here as it is the most straightforward tool for the job (that I am aware of). We assume that, if it does degrade performance, it does so in a roughly uniform way across the different packages and therefore we assume that the "Speedups" are roughly accurate.
- While these benchmarks are not too difficult to implement for the packages currently included and for basic cases, it becomes more challenging for certain packages and more complex cases. If you would like to see benchmarks for one of these more challenging packages or cases, please consider contributing the benchmarks yourself (see Contributing below).

---

## Contributing

If you are a developer/contributor/maintainer/user of a similar package with overlapping functionality and you would like it to be included in these benchmarks, please do the following:

- Create a benchmark script for your package with an implementation of the case(s) that will be run with appropriate arguments (see `numbacs_benchmark_ftle.py`)
- Create a runner script for your package (see `numbacs_runner.py`)
- Update `noxfile.py` with your package/case(s)

If you are proposing a case which is not yet implemented in the `NumbaCS` benchmarks, please open an issue with your proposed package/case(s) in this repository and I will do my best to respond promptly and let you know if/when I would be able to create the corresponding `NumbaCS` case.
