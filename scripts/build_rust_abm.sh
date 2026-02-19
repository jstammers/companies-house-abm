#!/usr/bin/env bash
# build_rust_abm.sh — Build and install the Rust ABM extension
#
# Usage:
#   ./scripts/build_rust_abm.sh            # release build (default)
#   ./scripts/build_rust_abm.sh --dev      # debug build (faster compile)
#
# After running this script, `companies_house_abm._rust_abm` can be imported
# from within the project's Python environment.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUST_DIR="$PROJECT_ROOT/rust_abm"
TARGET_DIR="$PROJECT_ROOT/src/companies_house_abm"
WHEEL_OUT="/tmp/rust_abm_build_$$"

PROFILE="release"
MATURIN_FLAGS="--release"

if [[ "${1:-}" == "--dev" ]]; then
    PROFILE="debug"
    MATURIN_FLAGS=""
    echo "Building in DEBUG mode (faster compile, slower runtime)"
else
    echo "Building in RELEASE mode (optimised for benchmarks)"
fi

# Check dependencies
command -v maturin >/dev/null 2>&1 || { echo "Error: maturin not found. Install with: pip install maturin"; exit 1; }
command -v cargo >/dev/null 2>&1 || { echo "Error: cargo not found. Install Rust from https://rustup.rs"; exit 1; }

echo
echo "Building Rust ABM extension..."
echo "  Source:  $RUST_DIR"
echo "  Install: $TARGET_DIR"
echo

mkdir -p "$WHEEL_OUT"

# Build the wheel
cd "$RUST_DIR"
# shellcheck disable=SC2086
maturin build $MATURIN_FLAGS --out "$WHEEL_OUT" --no-default-features 2>&1

# Find the built wheel
WHEEL=$(ls "$WHEEL_OUT"/*.whl | head -1)
if [[ -z "$WHEEL" ]]; then
    echo "Error: No wheel found in $WHEEL_OUT"
    exit 1
fi

echo
echo "Extracting .so from wheel: $WHEEL"

# Extract the .so file and place it in the package directory
python3 - <<PYTHON
import zipfile, pathlib, sys

wheel = '$WHEEL'
target = pathlib.Path('$TARGET_DIR')

z = zipfile.ZipFile(wheel)
so_files = [n for n in z.namelist() if n.endswith('.so')]

if not so_files:
    print('ERROR: No .so files found in wheel', file=sys.stderr)
    sys.exit(1)

for so_path in so_files:
    basename = pathlib.Path(so_path).name
    dest = target / basename
    dest.write_bytes(z.read(so_path))
    print(f'Installed: {dest}')
    print(f'  Size:    {dest.stat().st_size:,} bytes')
PYTHON

# Clean up
rm -rf "$WHEEL_OUT"

echo
echo "Done! Rust ABM extension installed."
echo "Test with:"
echo "  uv run python -c \"from companies_house_abm import _rust_abm; print(_rust_abm.run_simulation(n_firms=100, n_households=500, n_banks=10, periods=5, seed=42))\""
