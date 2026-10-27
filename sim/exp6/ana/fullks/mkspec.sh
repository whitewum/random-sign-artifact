#!/usr/bin/env bash
# Build the fullks SPEC on the server: cd $ROOT/out && bash mkspec.sh > spec.tsv
# critical: out/v; low, k = 3: out/v2; low, k = 4, 5: planted from out/v2s, direct from out/v3a
# (two configurations) or out/v3b + out/v3c merged (the other six), as in the final V-low report.
set -euo pipefail
dirs() { ls -d "$@" 2>/dev/null | tr '\n' ' '; }
for id in $(ls v | sed -n 's/^v-plant-\(.*\)-b[0-9]*$/\1/p' | sort -u); do
  printf 'critical\t%s\t%s\t%s\n' "$id" "$(dirs v/v-direct-$id-b*)" "$(dirs v/v-plant-$id-b*)"
done
for id in $(ls v2 | sed -n 's/^v2-plant-\(.*\)-b[0-9]*$/\1/p' | sort -u); do
  printf 'low\t%s\t%s\t%s\n' "$id" "$(dirs v2/v2-direct-$id-b*)" "$(dirs v2/v2-plant-$id-b*)"
done
for id in $(ls v2s | sed -n 's/^v2s-plant-\(.*\)-b[0-9]*$/\1/p' | sort -u); do
  if ls -d v3a/v3a-direct-$id-b* >/dev/null 2>&1; then d=$(dirs v3a/v3a-direct-$id-b*)
  else d="$(dirs v3b/v3b-direct-$id-b*) $(dirs v3c/v3c-direct-$id-b*)"; fi
  printf 'low\t%s\t%s\t%s\n' "$id" "$d" "$(dirs v2s/v2s-plant-$id-b*)"
done
