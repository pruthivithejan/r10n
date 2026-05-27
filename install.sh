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
CURL_FLAGS="-fsSL --retry 3 --retry-delay 2 --retry-connrefused"

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

downloaded=0
echo "Downloading $APP_NAME $VERSION for $uname_s/$arch..."

if [ -n "$RELEASE_API_URL" ] \
  && curl $CURL_FLAGS -H "Accept: application/vnd.github+json" "$RELEASE_API_URL" -o "$release_json_path"; then
  binary_url=$(asset_url_from_release_json "$asset")
  checksum_url=$(asset_url_from_release_json "SHA256SUMS")

  if [ -n "$binary_url" ] && [ -n "$checksum_url" ]; then
    rm -f "$binary_path" "$checksum_path"
    if curl $CURL_FLAGS "$binary_url" -o "$binary_path" \
      && curl $CURL_FLAGS "$checksum_url" -o "$checksum_path"; then
      downloaded=1
    fi
  fi
fi

for base_url in $BASE_URLS; do
  if [ "$downloaded" -ne 1 ]; then
    rm -f "$binary_path" "$checksum_path"
    if curl $CURL_FLAGS "$base_url/$asset" -o "$binary_path" \
      && curl $CURL_FLAGS "$base_url/SHA256SUMS" -o "$checksum_path"; then
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

case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo "Note: $INSTALL_DIR is not on your PATH."
    echo "Add it with: export PATH=\"$INSTALL_DIR:\$PATH\""
    ;;
esac
