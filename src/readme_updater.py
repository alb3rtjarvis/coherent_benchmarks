import pandas as pd
import json
import glob
import os
import numpy as np
import sys
import re
import argparse

# Configuration
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
RESULTS_DIR = os.path.join(REPO_ROOT, "results")
README_FILE = os.path.join(REPO_ROOT, "README.md")

# Directory to save individual .md files for each benchmark case section
MARKDOWN_DIR = os.path.join(RESULTS_DIR, "md_tables") 

SPEEDUP_BASELINE_PACKAGE = "NumbaCS" 

BENCHMARK_SECTION_START_PLACEHOLDER = "<!-- BENCHMARK_RESULTS_START -->"
BENCHMARK_SECTION_END_PLACEHOLDER = "<!-- BENCHMARK_RESULTS_END -->"


def load_benchmark_data(results_dir_path):
    """Loads data from *_results.json files."""
    all_data = []
    json_files = glob.glob(os.path.join(results_dir_path, "*_results.json"))
    print(f"Found {len(json_files)} '*_results.json' files in '{results_dir_path}'.")
    for f_path in json_files:
        filename = os.path.basename(f_path)
        if "_error" in filename.lower():
            continue
        print(f"  Processing: {filename}")
        try:
            with open(f_path, 'r', encoding='utf-8') as f: 
                data = json.load(f)
            metadata = data["metadata"]; params = data["parameters"]
            timing_data = data["timings"]
            record = {
                "package": metadata["package_name"], 
                "case_id": metadata["case_id"],
                "case_description": metadata.get(
                    "case_description", metadata["case_id"].replace("_", " ").upper()
                ),
                "iterates_per_run": int(params["iterates_per_run"]),
                "num_benchmark_runs": int(params["num_benchmark_runs"]),
                "mean_iter_s": float(timing_data["mean_per_iter_time"]),
                "std_iter_s": float(timing_data.get("std_per_iter_time", np.nan)),
                "mae": float(data.get("error_metrics", {}).get("mae", np.nan))
            }
            all_data.append(record)
        except Exception as e:
            print(f"    ERROR processing {filename}: {e}. Skipping.", file=sys.stderr)
    if not all_data: 
        print("WARNING: No valid benchmark data loaded.")
        
    return pd.DataFrame(all_data) if all_data else pd.DataFrame()

def _speedup_col_fmt(speedup):
    """
    Formats the speedup column so speedup appears normally and slowdown
    appears as (1/speedup)^{-1}
    """
    if pd.notnull(speedup) and speedup >= 1.0:
        return f"{speedup:.2f}"
    elif pd.notnull(speedup) and 0.0 < speedup < 1.0:        
        return f"({1/speedup:.2f})\u207B\u00B9"
    else:
        return "N/A"
    
def generate_md_tables(df, output_dir):
    """
    Generates a markdown file (Header + Table) for each case and saves it.
    Returns a list of file paths to the generated .md files, sorted by case_id.
    """
    if df.empty:
        return []

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created directory for cases: {output_dir}")

    generated_file_paths = []
    sorted_case_ids = sorted(df["case_id"].unique())

    for case_id in sorted_case_ids:
        group = df[df["case_id"] == case_id].copy()
        if group.empty:
            continue

        print(f"\nGenerating markdown for case: {case_id}")
        
        iter_p_run = group["iterates_per_run"].iloc[0]
        num_b_runs = group["num_benchmark_runs"].iloc[0]
        case_desc = group["case_description"].iloc[0]
        
        header_line = f"### {case_desc} (Iter/Run: {iter_p_run}, Num Runs: {num_b_runs})"
        
        # --- Prepare table data ---
        table_data = group[["package", "mean_iter_s"]].copy()
        table_data.rename(
            columns={"package": "Package", "mean_iter_s": "Mean /Iter (s)"}, inplace=True
        )
        if num_b_runs > 1 and 'std_iter_s' in group.columns and group['std_iter_s'].notna().any():
            table_data["Std /Iter (s)"] = group["std_iter_s"]
        if 'mae' in group.columns and group['mae'].notna().any():
            table_data["MAE"] = group["mae"]
        speedup_col_name = f"Speedup (vs {SPEEDUP_BASELINE_PACKAGE})"
        baseline_row = group[group["package"] == SPEEDUP_BASELINE_PACKAGE]
        if not baseline_row.empty:
            baseline_time = baseline_row["mean_iter_s"].iloc[0]
            if baseline_time > 0: 
                table_data[speedup_col_name] = pd.to_numeric(
                    baseline_time/group["mean_iter_s"], errors='coerce'
                )
            else: 
                table_data[speedup_col_name] = np.nan
        else: 
            table_data[speedup_col_name] = np.nan
        
        desired_cols_order = ["Package", "Mean /Iter (s)"]
        if "Std /Iter (s)" in table_data.columns: 
            desired_cols_order.append("Std /Iter (s)")
        if speedup_col_name in table_data.columns: 
            desired_cols_order.append(speedup_col_name)
        if "MAE" in table_data.columns: 
            desired_cols_order.append("MAE")
        current_cols = set(table_data.columns)
        ordered_cols = [col for col in desired_cols_order if col in current_cols] \
                       + [col for col in current_cols if col not in desired_cols_order]
        table_data = table_data[ordered_cols]
        formatters = {
            "Mean /Iter (s)": "{:.4f}", "Std /Iter (s)": "{:.4f}", "MAE": "{:.3e}",
            speedup_col_name: _speedup_col_fmt
        }
        for col, fmt in formatters.items():
            if col in table_data.columns: 
                table_data[col] = table_data[col].apply(
                    fmt if callable(fmt) else lambda x, f=fmt: f.format(x) if pd.notnull(x) else 'N/A'
                )
        case_table_md = table_data.to_markdown(index=False)
        # --- End Table Preparation ---

        # Combine header and table for this case
        case_full_markdown_name = f"{header_line}\n\n{case_table_md}"
        
        # Save to file
        file_path = os.path.join(output_dir, f"{case_id}_benchmark_section.md")
        try:
            with open(file_path, 'w', encoding='utf-8') as f_out:
                f_out.write(case_full_markdown_name)
            generated_file_paths.append(file_path)
            print(f"  Saved case table: {file_path}")
        except IOError as e:
            print(
                f"  ERROR: Could not write table for {case_id} to {file_path}: {e}", 
                file=sys.stderr
            )
            
    return generated_file_paths


def assemble_and_update_readme(readme_filepath, sorted_table_filepaths):
    """
    Assembles content from individual case markdown files and updates the README.
    """
    if not sorted_table_filepaths:
        full_benchmark_content_md = "No benchmark results to display at this time."
    else:
        all_case_contents = []
        for table_path in sorted_table_filepaths:
            try:
                with open(table_path, 'r', encoding='utf-8') as f_table:
                    all_case_contents.append(f_table.read())
            except FileNotFoundError:
                print(f"Warning: Table file not found: {table_path}. Skipping.", file=sys.stderr)
        
        # Join with a separator
        full_benchmark_content_md = ("\n\n---\n\n").join(all_case_contents)

    # --- README Update Logic ---
    try:
        with open(readme_filepath, 'r', encoding='utf-8') as f: 
            readme_text = f.read()
    except FileNotFoundError:
        print(f"ERROR: README file not found at '{readme_filepath}'. Cannot update.", file=sys.stderr)
        return False

    pattern = re.compile(
        f"({re.escape(BENCHMARK_SECTION_START_PLACEHOLDER)})(.*?)"
        f"({re.escape(BENCHMARK_SECTION_END_PLACEHOLDER)})", 
        re.DOTALL
    )
    match = pattern.search(readme_text)

    if not match:
        print(
            f"ERROR: Master placeholders not found in '{readme_filepath}'. See instructions.", 
            file=sys.stderr
        )
        return False

    new_block_content = f"{match.group(1)}\n\n{full_benchmark_content_md.strip()}\n\n{match.group(3)}"
    updated_readme_text = readme_text[:match.start()] + new_block_content + readme_text[match.end():]

    if updated_readme_text != readme_text:
        try:
            final_content_to_write = updated_readme_text.strip() + "\n"
            with open(readme_filepath, 'w', encoding='utf-8', newline='\n') as f: 
                f.write(final_content_to_write)
            print(f"Successfully updated benchmark section in '{readme_filepath}'.")
            return True
        except Exception as e:
            print(f"ERROR writing to '{readme_filepath}': {e}", file=sys.stderr)
            return False
    else:
        print(f"No changes needed for benchmark section in '{readme_filepath}'.")
        return True


def main():
    df_benchmarks = load_benchmark_data(RESULTS_DIR)
    if df_benchmarks.empty:
        print("No benchmark data processed.")
        # Do nothing if no benchmark data found
        return
    
    parser = argparse.ArgumentParser(
        description="Default (no args): generate tables and update README.md, "
        + "tables-only: generate tables only"
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        choices=["all", "tables-only"],
        help="Pass 'tables-only' as arg to generate tables WITHOUT updating README.md, "
            + "otherwise README.md will be updated with generated tables."
        )
    args = parser.parse_args()
    
    if args.mode == "tables-only":
        print(f"{__file__}: Starting benchmark reporting (generating tables for each case)...")
        # Generate and save .md file for each case (Header + Table)
        case_table_filepaths = generate_md_tables(df_benchmarks, MARKDOWN_DIR)
        if not case_table_filepaths:
            print("No individual case markdown files were generated.")
            return
        print(f"{__file__}: Process complete.")
    else:
        print(f"{__file__}: Starting benchmark reporting (individual case files -> README section)...")
    
        # Generate and save .md file for each case (Header + Table)
        case_table_filepaths = generate_md_tables(df_benchmarks, MARKDOWN_DIR)
        
        if not case_table_filepaths:
            print("No individual case markdown files were generated.")
            # Do nothing if no markdown files generated
            return
    
        # Assemble content from these files and update the README's master benchmark section
        assemble_and_update_readme(README_FILE, case_table_filepaths)
        
        print(f"{__file__}: Process complete.")

if __name__ == "__main__":
    main()