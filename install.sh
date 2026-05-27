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

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to install $APP_NAME" >&2
  exit 1
fi

case "$VERSION" in
  latest)
    BASE_URLS=${R10N_DOWNLOAD_URL:-"https://github.com/${REPO}/releases/latest/download"}
    ;;
  v*)
    BASE_URLS=${R10N_DOWNLOAD_URL:-"https://github.com/${REPO}/releases/download/${VERSION}"}
    ;;
  *)
    BASE_URLS=${R10N_DOWNLOAD_URL:-"https://github.com/${REPO}/releases/download/v${VERSION}"}
    ;;
esac

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
    asset="r10n-linux-x86_64"
    ;;
  darwin/arm64)
    asset="r10n-macos-arm64"
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

binary_path="$tmp_dir/$asset"
checksum_path="$tmp_dir/SHA256SUMS"

downloaded=0
for base_url in $BASE_URLS; do
  rm -f "$binary_path" "$checksum_path"
  if curl -fsSL --retry 3 --retry-delay 2 --retry-connrefused "$base_url/$asset" -o "$binary_path" \
    && curl -fsSL --retry 3 --retry-delay 2 --retry-connrefused "$base_url/SHA256SUMS" -o "$checksum_path"; then
    downloaded=1
    break
  fi
done

if [ "$downloaded" -ne 1 ]; then
  echo "Failed to download $asset from release assets" >&2
  exit 1
fi

expected_hash=$(awk -v name="$asset" '$2 == name || $2 == "*"name { print $1; exit }' "$checksum_path")
if [ -z "$expected_hash" ]; then
  echo "Could not find checksum for $asset" >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  actual_hash=$(sha256sum "$binary_path" | awk '{ print $1 }')
elif command -v shasum >/dev/null 2>&1; then
  actual_hash=$(shasum -a 256 "$binary_path" | awk '{ print $1 }')
else
  echo "No SHA-256 tool found (sha256sum or shasum required)." >&2
  exit 1
fi

if [ "$actual_hash" != "$expected_hash" ]; then
  echo "Checksum verification failed for $asset" >&2
  exit 1
fi

mkdir -p "$INSTALL_DIR"
install -m 755 "$binary_path" "$INSTALL_DIR/r10n"

echo "Installed $APP_NAME to $INSTALL_DIR/r10n"
echo "Run: r10n --help"
