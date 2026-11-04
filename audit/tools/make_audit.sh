#!/bin/bash
# `make audit`. Clones the committed repo to a clean folder, fills the path tokens, overlays the data from DATA_DIR, builds fresh pinned environments, reruns every stage, and compares output hashes with the committed files.
# Usage: DATA_DIR=<folder> bash audit/tools/make_audit.sh <workdir> [full|public]
# full needs the broker exports as well. public still runs the stages listed in tools/stages_broker.txt, because some build sandboxes that later stages use, but does not count their failure. See REPRODUCE.md.
set -u
SRC=$(cd "$(dirname "$0")/../.." && pwd)
WORK=${1:-$SRC/../_audit_clean}
export TIER=${2:-full}
DATA_DIR=${DATA_DIR:-$SRC/data/raw}
case "$DATA_DIR" in /*|[A-Za-z]:*) ;; *) DATA_DIR="$PWD/$DATA_DIR" ;; esac
export DATA_DIR
mkdir -p "$WORK" && WORK=$(cd "$WORK" && pwd)
rm -rf -- "$WORK/repo"
git -c safe.directory='*' clone -q "$SRC" "$WORK/repo" || exit 1
cd "$WORK/repo" || exit 1
BASE=${PYTHON311:-python}
$BASE -c 'import sys; assert sys.version_info[:2] == (3, 11), "Python 3.11 is required, set PYTHON311"' || exit 1
if [ -d /c/Windows ]; then VB=Scripts; X=.exe; export PSEP=";"; else VB=bin; X=; export PSEP=":"; fi
env_make() { # folder, requirements
  $BASE -m venv "$1" && "$1/$VB/python$X" -m pip install -q --disable-pip-version-check ${PIP_EXTRA:-} --upgrade pip && "$1/$VB/python$X" -m pip install -q --disable-pip-version-check ${PIP_EXTRA:-} -r "$2"
}
env_make audit/.venv_audit audit/infrastructure/requirements_audit_env.txt || exit 1
env_make audit/.venv_gb audit/infrastructure/requirements_goldbot_venv.txt || exit 1
env_make audit/.venv_ls audit/infrastructure/requirements_labelsizing_env.txt || exit 1
A=$WORK/repo/audit
export PY="$A/.venv_gb/$VB/python$X" PA="$A/.venv_audit/$VB/python$X" PL="$A/.venv_ls/$VB/python$X" SRC=$SRC/audit
$PA -B audit/tools/render_paths.py "$WORK/repo" || exit 1
$PA -B audit/tools/assemble_data.py "$WORK/repo" "$DATA_DIR" "$TIER" || exit 1
cd audit || exit 1
bash tools/run_all.sh
$PA -B tools/check_hashes.py "$SRC" "$WORK/repo/audit" "$WORK/repo" "$TIER"
