#!/usr/bin/env bash
set -uo pipefail
D="research/flysoar_dossier.md"
S="research/sources.md"
mkdir -p research
[[ -f "$D" ]] || touch "$D"
[[ -f "$S" ]] || touch "$S"
combined=$(mktemp)
cat "$D" "$S" > "$combined"
evidence_items=$(grep -Ei '(^[-*] |^#+ ).*(https?://|~/.codex|/home/faishal|Obsidian|vault:|source:)' "$combined" 2>/dev/null | wc -l | tr -d ' ')
source_urls=$(grep -Eoh 'https?://[^ )>]+' "$combined" 2>/dev/null | sort -u | wc -l | tr -d ' ')
sections_complete=0
for section in "Product" "Technical" "Competitors" "Founder" "Funding" "Founder-engineer fit" "Outreach"; do
  if grep -qi "^## .*${section}" "$D"; then
    if awk "/^## .*${section}/{flag=1;next}/^## /{flag=0}flag" "$D" | grep -Eq 'https?://|~/.codex|/home/faishal|vault:'; then
      sections_complete=$((sections_complete+1))
    fi
  fi
done
local_fit_signals=$(grep -Eih '(~/.codex|/home/faishal|vault:|Obsidian).*fit|fit.*(~/.codex|/home/faishal|vault:|Obsidian)|local signal|codex|obsidian' "$D" 2>/dev/null | wc -l | tr -d ' ')
rm -f "$combined"
echo "METRIC evidence_items=${evidence_items}"
echo "METRIC source_urls=${source_urls}"
echo "METRIC sections_complete=${sections_complete}"
echo "METRIC local_fit_signals=${local_fit_signals}"
