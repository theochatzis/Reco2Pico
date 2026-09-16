#!/usr/bin/env bash
# Usage:
#   ./tools/rucio_rules.sh [--lifetime-days DAYS] list [ACCOUNT|DATASET]
#   ./tools/rucio_rules.sh [--lifetime-days DAYS] add DATASET [RSE]
#   ./tools/rucio_rules.sh [--lifetime-days DAYS] add-fraction DATASET FRACTION [RSE]
#   ./tools/rucio_rules.sh [--lifetime-days DAYS] add-auto DATASET
#   ./tools/rucio_rules.sh sites
#   ./tools/rucio_rules.sh delete RULE_ID

set -euo pipefail

export RUCIO_ACCOUNT="${RUCIO_ACCOUNT:-${USER}}"
RUCIO_SETUP="${RUCIO_SETUP:-/cvmfs/cms.cern.ch/rucio/setup-py3.sh}"
RUCIO_TARGET_RSE="${RUCIO_TARGET_RSE:-T2_FI_HIP}"
RUCIO_LIFETIME="${RUCIO_LIFETIME:-15552000}" # 180 days
CRAB_USABLESITE_JSON="${CRAB_USABLESITE_JSON:-https://cmssst.web.cern.ch/cmssst/analysis/usableSites.json}"

usage() {
  printf '%s\n' \
    "Usage:" \
    "  $0 [--lifetime-days DAYS] list [ACCOUNT|DATASET]" \
    "  $0 [--lifetime-days DAYS] add DATASET [RSE]" \
    "  $0 [--lifetime-days DAYS] add-fraction DATASET FRACTION [RSE]" \
    "  $0 [--lifetime-days DAYS] add-auto DATASET" \
    "  $0 sites" \
    "  $0 delete RULE_ID" \
    "" \
    "Environment overrides:" \
    "  RUCIO_ACCOUNT=$RUCIO_ACCOUNT" \
    "  RUCIO_TARGET_RSE=$RUCIO_TARGET_RSE" \
    "  RUCIO_LIFETIME=$RUCIO_LIFETIME"
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command is unavailable: $1"
}

ensure_rucio() {
  if ! command -v rucio >/dev/null 2>&1; then
    [[ -r "$RUCIO_SETUP" ]] || die "Rucio setup is unavailable: $RUCIO_SETUP"
    # shellcheck disable=SC1090
    source "$RUCIO_SETUP"
  fi
  require_command rucio
}

normalise_did() {
  case "$1" in
    *:*) printf '%s\n' "$1" ;;
    /*) printf 'cms:%s\n' "$1" ;;
    *) die "expected /PRIMARY/PROCESSING/TIER or a scoped Rucio DID" ;;
  esac
}

get_crab_usable_sites() {
  require_command curl
  require_command jq
  curl -fsSL "$CRAB_USABLESITE_JSON" | jq -r '
    .[]
    | select(.value == "usable" and (.name | test("^T[12]_")))
    | if (.name | test("^T1_")) then .name + "_Disk" else .name end
  '
}

crab_site_expression() {
  local sites=()
  mapfile -t sites < <(get_crab_usable_sites)
  if (( ${#sites[@]} == 0 )); then
    die "the CRAB usable-site service returned no T1/T2 sites"
  fi
  local IFS='|'
  printf '%s\n' "${sites[*]}"
}

add_rule() {
  local did rse
  did=$(normalise_did "$1")
  rse=$2
  printf 'Dataset:  %s\nTarget:   %s\nLifetime: %s seconds\n' \
    "$did" "$rse" "$RUCIO_LIFETIME"
  rucio add-rule \
    "$did" \
    1 \
    "$rse" \
    --lifetime "$RUCIO_LIFETIME" \
    --activity "User" \
    --ask-approval \
    --grouping "ALL" \
    --skip-duplicates
}

add_fraction_rule() (
  local source_did fraction rse temp_dir all_files selected_files
  local total selected source_tag fraction_tag timestamp subset_did
  source_did=$(normalise_did "$1")
  fraction=$2
  rse=$3

  awk -v fraction="$fraction" \
    'BEGIN { exit !(fraction > 0 && fraction <= 1) }' ||
    die "FRACTION must be greater than 0 and no greater than 1"

  temp_dir=$(mktemp -d)
  trap 'rm -rf "$temp_dir"' EXIT
  all_files="$temp_dir/all_files.txt"
  selected_files="$temp_dir/selected_files.txt"

  printf 'Reading files from %s\n' "$source_did"
  rucio list-files --csv "$source_did" |
    cut -d, -f1 |
    LC_ALL=C sort -u > "$all_files"

  total=$(wc -l < "$all_files")
  (( total > 0 )) || die "the source dataset contains no files"
  selected=$(awk -v total="$total" -v fraction="$fraction" \
    'BEGIN { print int(total * fraction + 0.999999999) }')
  head -n "$selected" "$all_files" > "$selected_files"

  source_tag=$(printf '%s' "$source_did" |
    sed -E 's/^[^:]+://; s#[^A-Za-z0-9._-]+#_#g' |
    cut -c1-72)
  fraction_tag=${fraction//./p}
  timestamp=$(date -u +%Y%m%dT%H%M%SZ)
  subset_did="user.${RUCIO_ACCOUNT}:user.${RUCIO_ACCOUNT}.reco2pico.${source_tag}.f${fraction_tag}.${timestamp}"

  printf 'Selected: %d/%d files\nSubset:   %s\n' \
    "$selected" "$total" "$subset_did"
  rucio add-dataset "$subset_did" --lifetime "$RUCIO_LIFETIME"
  rucio attach --from-file "$subset_did" "$selected_files"
  add_rule "$subset_did" "$rse"
)

while (( $# > 0 )); do
  case "$1" in
    --lifetime-days)
      (( $# >= 2 )) || die "--lifetime-days requires a value"
      [[ "$2" =~ ^[1-9][0-9]*$ ]] ||
        die "--lifetime-days must be a positive integer"
      RUCIO_LIFETIME=$((10#$2 * 86400))
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

command_name="${1:-help}"
if (( $# > 0 )); then
  shift
fi

case "$command_name" in
  list)
    (( $# <= 1 )) || die "list accepts at most one account or dataset"
    ensure_rucio
    if (( $# == 0 )); then
      rucio list-rules --account "$RUCIO_ACCOUNT"
    elif [[ "$1" == /* || "$1" == *:* ]]; then
      rucio list-rules "$(normalise_did "$1")"
    else
      rucio list-rules --account "$1"
    fi
    ;;

  add)
    (( $# >= 1 && $# <= 2 )) || die "add requires DATASET and optionally RSE"
    ensure_rucio
    add_rule "$1" "${2:-$RUCIO_TARGET_RSE}"
    ;;

  add-fraction)
    (( $# >= 2 && $# <= 3 )) ||
      die "add-fraction requires DATASET, FRACTION, and optionally RSE"
    ensure_rucio
    add_fraction_rule "$1" "$2" "${3:-$RUCIO_TARGET_RSE}"
    ;;

  add-auto)
    (( $# == 1 )) || die "add-auto requires exactly one DATASET"
    ensure_rucio
    add_rule "$1" "$(crab_site_expression)"
    ;;

  sites)
    (( $# == 0 )) || die "sites accepts no arguments"
    get_crab_usable_sites
    ;;

  delete)
    (( $# == 1 )) || die "delete requires exactly one RULE_ID"
    ensure_rucio
    printf 'Delete Rucio rule %s? [y/N] ' "$1"
    read -r answer
    [[ "$answer" == "y" || "$answer" == "Y" ]] || {
      printf 'Rule was not deleted.\n'
      exit 0
    }
    rucio delete-rule "$1"
    ;;

  help|-h|--help)
    usage
    ;;

  *)
    usage >&2
    die "unknown command: $command_name"
    ;;
esac
