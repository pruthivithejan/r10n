#!/bin/sh

set -eu

REPO="pruthivithejan/r10n"
INSTALL_DIR="${R10N_INSTALL_DIR:-$HOME/.local/bin}"
VERSION="latest"

usage() {
  cat <<'EOF'
Install r10n binary from GitHub Releases.

Usage:
  install.sh [--version <tag>] [--install-dir <path>]

Options:
  --version      Release tag to install (for example: v2.0.0 or 2.0.0)
  --install-dir  Install directory (default: ~/.local/bin)
  -h, --help     Show this help message

Environment:
  R10N_INSTALL_DIR  Override install directory
EOF
}

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
  echo "curl is required to install r10n" >&2
  exit 1
fi

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
    echo "Download a matching binary manually from GitHub Releases." >&2
    exit 1
    ;;
esac

if [ "$VERSION" = "latest" ]; then
  base_url="https://github.com/${REPO}/releases/latest/download"
else
  case "$VERSION" in
    v*)
      tag="$VERSION"
      ;;
    *)
      tag="v$VERSION"
      ;;
  esac
  base_url="https://github.com/${REPO}/releases/download/${tag}"
fi

tmp_dir=$(mktemp -d)
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT INT TERM

binary_path="$tmp_dir/$asset"
checksum_path="$tmp_dir/SHA256SUMS"

echo "Downloading $asset..."
curl -fL "$base_url/$asset" -o "$binary_path"

echo "Downloading SHA256SUMS..."
curl -fL "$base_url/SHA256SUMS" -o "$checksum_path"

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

echo "Installed r10n to $INSTALL_DIR/r10n"
echo "Run: r10n --help"
echo "Update later with: r10n upgrade"

case ":$PATH:" in
  *":$INSTALL_DIR:"*)
    ;;
  *)
    echo ""
    echo "Add this directory to your PATH if needed:"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
    ;;
esac
