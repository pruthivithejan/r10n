#!/bin/sh
# shellcheck shell=dash
# shellcheck disable=SC2039
# shellcheck disable=SC2268

set -eu

APP_NAME="r10n"
REPO="pruthivithejan/r10n"

usage() {
  cat <<'EOF'
r10n installer

Usage:
  install.sh [--version <tag>] [--install-dir <path>]

Options:
  --version      Release tag to install (for example: v0.5.1 or 0.5.1)
  --install-dir  Install directory (default: ~/.local/bin)
  -h, --help     Show this help message

Environment:
  R10N_INSTALL_DIR  Override install directory
  R10N_DOWNLOAD_URL  Override the release download base URL
EOF
}

VERSION="latest"
INSTALL_DIR="${R10N_INSTALL_DIR:-$HOME/.local/bin}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --version)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --version" >&2
        exit 1
      fi
      VERSION="$2"
      shift 2
      ;;
    --install-dir)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --install-dir" >&2
        exit 1
      fi
      INSTALL_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

uname_s=$(uname -s | tr '[:upper:]' '[:lower:]')
uname_m=$(uname -m | tr '[:upper:]' '[:lower:]')

case "$uname_m" in
  amd64|x64)
    arch="x86_64"
    ;;
  aarch64)
    arch="arm64"
    ;;
  *)
    arch="$uname_m"
    ;;
esac

case "$uname_s/$arch" in
  linux/x86_64)
    asset="r10n-linux-x86_64.tar.gz"
    ;;
  darwin/arm64)
    asset="r10n-macos-arm64.tar.gz"
    ;;
  *)
    echo "Unsupported platform: $uname_s/$arch" >&2
    exit 1
    ;;
esac

tmp_dir=$(mktemp -d)
cleanup() { rm -rf "$tmp_dir"; }
abort() {
  cleanup
  exit 130
}
trap cleanup EXIT
trap abort INT TERM

artifact_path="$tmp_dir/$asset"
checksum_path="$tmp_dir/SHA256SUMS"
release_json_path="$tmp_dir/release.json"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to install $APP_NAME" >&2
  exit 1
fi

if [ -n "${R10N_DOWNLOAD_URL:-}" ]; then
  RELEASE_API_URL=""
  BASE_URLS="$R10N_DOWNLOAD_URL"
else
  case "$VERSION" in
    latest)
      RELEASE_API_URL="https://api.github.com/repos/${REPO}/releases/latest"
      BASE_URLS="https://github.com/${REPO}/releases/latest/download"
      ;;
    v*)
      RELEASE_API_URL="https://api.github.com/repos/${REPO}/releases/tags/${VERSION}"
      BASE_URLS="https://github.com/${REPO}/releases/download/${VERSION}"
      ;;
    *)
      RELEASE_API_URL="https://api.github.com/repos/${REPO}/releases/tags/v${VERSION}"
      BASE_URLS="https://github.com/${REPO}/releases/download/v${VERSION}"
      ;;
  esac
fi

asset_url_from_release_json() {
  name="$1"
  awk -v name="$name" '
    /"name":[[:space:]]*"/ {
      in_asset = ($0 ~ "\"name\":[[:space:]]*\"" name "\"")
    }
    in_asset && /"browser_download_url":[[:space:]]*"/ {
      sub(/.*"browser_download_url":[[:space:]]*"/, "")
      sub(/".*/, "")
      print
      exit
    }
  ' "$release_json_path"
}

asset_size_from_release_json() {
  name="$1"
  awk -v name="$name" '
    /"name":[[:space:]]*"/ {
      in_asset = ($0 ~ "\"name\":[[:space:]]*\"" name "\"")
    }
    in_asset && /"size":[[:space:]]*[0-9]+/ {
      sub(/.*"size":[[:space:]]*/, "")
      sub(/,.*/, "")
      sub(/[[:space:]]*}.*/, "")
      print
      exit
    }
  ' "$release_json_path"
}

download_binary_asset() {
  download_url="$1"
  destination="$2"
  use_color=0
  if [ -t 2 ] && [ "${TERM:-}" != "dumb" ] && [ -z "${NO_COLOR:-}" ] && [ "${R10N_ACCESSIBLE:-}" != "1" ]; then
    use_color=1
  fi
  if [ "${brand_displayed:-0}" -eq 0 ]; then
    if [ "$use_color" -eq 1 ]; then
      case "${R10N_THEME:-dark}" in
        light) printf '\033[38;2;0;88;184m' >&2 ;;
        *) printf '\033[38;2;18;247;214m' >&2 ;;
      esac
    fi
    if [ "${R10N_ACCESSIBLE:-}" != "1" ]; then
      # BEGIN GENERATED R10N ASCII
      printf '%s\n' \
        '▀▀▀▀▀▀     ▀▀    ▀▀▀▀▀   ▀▀   ▀▀' \
        '▀▀   ▀▀   ▀▀▀   ▀▀   ▀▀  ▀▀▀  ▀▀' \
        '▀▀   ▀▀    ▀▀   ▀▀   ▀▀  ▀▀▀▀ ▀▀' \
        '▀▀▀▀▀▀     ▀▀   ▀▀   ▀▀  ▀▀ ▀▀▀▀' \
        '▀▀ ▀▀      ▀▀   ▀▀   ▀▀  ▀▀  ▀▀▀' \
        '▀▀  ▀▀     ▀▀   ▀▀   ▀▀  ▀▀   ▀▀' \
        '▀▀   ▀▀  ▀▀▀▀▀▀  ▀▀▀▀▀   ▀▀   ▀▀' >&2
      # END GENERATED R10N ASCII
    else
      printf 'r10n — routine automation\n' >&2
    fi
    if [ "$use_color" -eq 1 ]; then
      printf '\033[0m' >&2
    fi
    if [ -n "${expected_asset_bytes:-}" ]; then
      expected_size_mb=$(awk -v bytes="$expected_asset_bytes" 'BEGIN { printf "%.1f MB", bytes / 1000000 }')
      printf 'Downloading %s (%s)...\n' "$asset" "$expected_size_mb" >&2
    else
      printf 'Downloading %s; total size unknown...\n' "$asset" >&2
    fi
    brand_displayed=1
  fi

  # Keep a live transfer meter when motion is allowed; accessible and reduced-motion
  # modes show the announced expected MB value and the actual MB total afterward.
  if [ -t 2 ] && [ "${R10N_ACCESSIBLE:-}" != "1" ] && [ "${R10N_NO_MOTION:-}" != "1" ]; then
    if [ "$use_color" -eq 1 ]; then
      case "${R10N_THEME:-dark}" in
        light) printf '\033[38;2;0;88;184m' >&2 ;;
        *) printf '\033[38;2;0;209;255m' >&2 ;;
      esac
    fi
    if ! curl -fL --progress-bar --retry 3 --retry-delay 2 --retry-connrefused \
      "$download_url" -o "$destination"; then
      if [ "$use_color" -eq 1 ]; then printf '\033[0m' >&2; fi
      return 1
    fi
    if [ "$use_color" -eq 1 ]; then printf '\033[0m' >&2; fi
  else
    if ! curl -fsSL --retry 3 --retry-delay 2 --retry-connrefused \
      "$download_url" -o "$destination"; then
      return 1
    fi
  fi

  downloaded_bytes=$(wc -c < "$destination" | tr -d '[:space:]')
  downloaded_mb=$(awk -v bytes="$downloaded_bytes" 'BEGIN { printf "%.1f MB", bytes / 1000000 }')
  if [ -n "${expected_asset_bytes:-}" ]; then
    expected_size_mb=$(awk -v bytes="$expected_asset_bytes" 'BEGIN { printf "%.1f MB", bytes / 1000000 }')
    printf 'Downloaded %s / %s.\n' "$downloaded_mb" "$expected_size_mb" >&2
  else
    printf 'Downloaded %s; release size unknown.\n' "$downloaded_mb" >&2
  fi
}

downloaded=0
echo "Downloading $APP_NAME $VERSION for $uname_s/$arch..."

if [ -n "$RELEASE_API_URL" ] \
  && curl -fsSL --retry 3 --retry-delay 2 --retry-connrefused \
    -H "Accept: application/vnd.github+json" "$RELEASE_API_URL" -o "$release_json_path"; then
  binary_url=$(asset_url_from_release_json "$asset")
  checksum_url=$(asset_url_from_release_json "SHA256SUMS")
  expected_asset_bytes=$(asset_size_from_release_json "$asset")

  if [ -n "$binary_url" ] && [ -n "$checksum_url" ]; then
    rm -f "$artifact_path" "$checksum_path"
    if download_binary_asset "$binary_url" "$artifact_path" \
      && curl -fsSL --retry 3 --retry-delay 2 --retry-connrefused "$checksum_url" -o "$checksum_path"; then
      downloaded=1
    fi
  fi
fi

for base_url in $BASE_URLS; do
  if [ "$downloaded" -ne 1 ]; then
    rm -f "$artifact_path" "$checksum_path"
    expected_asset_bytes=""
    if download_binary_asset "$base_url/$asset" "$artifact_path" \
      && curl -fsSL --retry 3 --retry-delay 2 --retry-connrefused \
        "$base_url/SHA256SUMS" -o "$checksum_path"; then
      downloaded=1
      break
    fi
  fi
done

if [ "$downloaded" -ne 1 ]; then
  echo "Failed to download $asset from release assets" >&2
  exit 1
fi

echo "Verifying checksum..."
expected_hash=$(awk -v name="$asset" '$2 == name || $2 == "*"name { print $1; exit }' "$checksum_path")
if [ -z "$expected_hash" ]; then
  echo "Could not find checksum for $asset" >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  actual_hash=$(sha256sum "$artifact_path" | awk '{ print $1 }')
elif command -v shasum >/dev/null 2>&1; then
  actual_hash=$(shasum -a 256 "$artifact_path" | awk '{ print $1 }')
else
  echo "No SHA-256 tool found (sha256sum or shasum required)." >&2
  exit 1
fi

if [ "$actual_hash" != "$expected_hash" ]; then
  echo "Checksum verification failed for $asset" >&2
  exit 1
fi

mkdir -p "$INSTALL_DIR"
tar -xzf "$artifact_path" -C "$tmp_dir"

if [ ! -x "$tmp_dir/r10n/r10n" ]; then
  echo "Release archive did not contain an executable r10n/r10n" >&2
  exit 1
fi

rm -rf "$INSTALL_DIR/.r10n.new" "$INSTALL_DIR/.r10n.bak"
mv "$tmp_dir/r10n" "$INSTALL_DIR/.r10n.new"

if [ -d "$INSTALL_DIR/.r10n" ]; then
  mv "$INSTALL_DIR/.r10n" "$INSTALL_DIR/.r10n.bak"
fi

mv "$INSTALL_DIR/.r10n.new" "$INSTALL_DIR/.r10n"
chmod 755 "$INSTALL_DIR/.r10n/r10n"
ln -sfn ".r10n/r10n" "$INSTALL_DIR/r10n.new"
mv -f "$INSTALL_DIR/r10n.new" "$INSTALL_DIR/r10n"
rm -rf "$INSTALL_DIR/.r10n.bak"

echo "Installed $APP_NAME to $INSTALL_DIR/r10n"
echo "Run: r10n --help"

case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo "Note: $INSTALL_DIR is not on your PATH."
    echo "Add it with: export PATH=\"$INSTALL_DIR:\$PATH\""
    ;;
esac
