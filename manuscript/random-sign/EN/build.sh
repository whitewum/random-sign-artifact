#!/usr/bin/env bash
set -euo pipefail
# Build the English manuscript: ./manuscript/random-sign/EN/build.sh
en_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
build_dir="$en_dir/build"
latexmk -g -pdf -interaction=nonstopmode -halt-on-error \
    -outdir="$build_dir" -cd "$en_dir/main.tex"
mv "$build_dir/main.pdf" "$en_dir/main.pdf"
if grep -E "(Citation|Reference) .* undefined" "$build_dir/main.log" >&2; then
    printf 'error: undefined citations or references\n' >&2
    exit 1
fi
