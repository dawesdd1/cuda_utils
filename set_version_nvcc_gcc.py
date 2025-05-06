import os
import argparse
import subprocess
import sys

def run(cmd, check=True):
    """Run a shell command, echoing it first."""
    print(f"[RUN] {cmd}")
    return subprocess.run(cmd, shell=True, check=check)

def capture(cmd):
    """Run a shell command and return its trimmed stdout."""
    return subprocess.check_output(cmd, shell=True).decode().strip()

def parse_args():
  """Simple arg parser with args for cuda install dir"""
    parser = argparse.ArgumentParser(
        description="Set up SuGaR conda env, GCC toolchain, CUDA, and extensions"
    )
    parser.add_argument(
        "--cuda_home", default='/usr/local/cuda-11.8',
        help="Path to CUDA (e.g. typically /usr/local/cuda-11.8). If unset, uses your default nvcc"
    )
    parser.add_argument(
        "--conda_env", default='sugar',
        help="Name of your conda environment (default: sugar)"
    )
    return parser.parse_args()


def main(args):
    env = args.conda_env

    # 1) Create or update sugar env
    print(f"[INFO] Checking for '{env}' conda environment…")
    envs_json = capture("conda env list --json")
    env_paths = json.loads(envs_json)["envs"]
    if not any(p.endswith(os.path.sep + env) for p in env_paths):
        print(f"[INFO] '{env}' not found; creating from environment.yml")
        run("conda env create -f environment.yml")
    else:
        print(f"[INFO] '{env}' exists; updating from environment.yml")
        run(f"conda env update -n {env} -f environment.yml")

    # 2) Install GCC/G++-11 to satisfy CUDA 11.8’s host compiler check
    print(f"[INFO] Installing GCC/G++ 11 into '{env}'…")
    run(f"conda install -n {env} -c conda-forge gcc_linux-64=11 gxx_linux-64=11 -y")

    # 3) Find the conda-provided compilers and export them
    cc_path  = capture(f"conda run -n {env} bash -lc 'which x86_64-conda-linux-gnu-cc'")
    cxx_path = capture(f"conda run -n {env} bash -lc 'which x86_64-conda-linux-gnu-c++'")
    os.environ["CC"]           = cc_path
    os.environ["CXX"]          = cxx_path
    os.environ["CUDAHOSTCXX"]  = cxx_path
    print(f"[INFO] export CC          = {cc_path}")
    print(f"[INFO] export CXX         = {cxx_path}")
    print(f"[INFO] export CUDAHOSTCXX = {cxx_path}")

    # 4) If requested, point at a specific CUDA install (and its libs)
    if args.cuda_home:
        cuda = args.cuda_home
        os.environ["CUDA_HOME"]         = cuda
        os.environ["PATH"]              = f"{cuda}/bin:" + os.environ["PATH"]
        os.environ["LD_LIBRARY_PATH"]   = f"{cuda}/lib64:" + os.environ.get("LD_LIBRARY_PATH", "")
        print(f"[INFO] export CUDA_HOME from: {cuda}")
        print(f"[INFO] export LD_LIBRARY_PATH to include: {cuda}/lib64")

    # 5) Verify versions
    print("[INFO] Verifying GCC/G++ and CUDA toolchain versions:")
    print(subprocess.check_output(f"{cc_path} --version", shell=True).decode())
    print(subprocess.check_output(f"{cxx_path} --version", shell=True).decode())
    nvcc_cmd = (
        f"{os.environ['CUDA_HOME']}/bin/nvcc"
        if args.cuda_home else
        "nvcc"
    )
    print(subprocess.check_output(f"{nvcc_cmd} --version", shell=True).decode())

    ...
