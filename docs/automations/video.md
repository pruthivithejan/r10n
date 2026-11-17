---
icon: lucide/clapperboard
---

# Asset Video

Turn exported images and PDF pages into a short MP4.

r10n uses your system `ffmpeg`. When it is missing, r10n installs it on demand
with the available package manager (Homebrew, MacPorts, apt, dnf, zypper,
pacman, apk, winget, Chocolatey, or Scoop).

## Run

Open the native form:

```bash
r10n video
```

Or pass the folder and order directly:

```bash
r10n video \
  --input /path/to/brand-export \
  --order "cover.png;guidelines.pdf:1-3;logo.png" \
  --yes
```

Quote `--order` when it contains semicolons so your shell does not split it.
Every slide defaults to half a second, 30fps, and 1920x1080 landscape output.

PDF pages stay in the order you list them:

```bash
r10n video \
  --input /path/to/brand-export \
  --order "guidelines.pdf:1,2,5,7,13,19,21-23,26" \
  --output /path/to/reel.mp4 \
  --yes
```

## Order syntax

References can be numbers from the folder listing, relative filenames, or plain
filenames when they are unique.

| Reference | Meaning |
|-----------|---------|
| `3` | Third asset in the scanned list |
| `logo.png` | Image by filename |
| `brand.pdf` | Every page of a PDF |
| `brand.pdf:1-3` | Pages 1 through 3 |
| `brand.pdf:1,4,6-8` | Pages 1, 4, and 6 through 8 |
| `brand.pdf:all` | Every page of that PDF |

Separate references with semicolons. Commas also work when no PDF page ranges
are involved:

```bash
--order "1;2;3"
--order "1,2,3"
--order "cover.png;brand.pdf:1,3-5;logo.png"
```

Omit `--order` to include every image and every PDF page in filename order.

## Parameters

| Parameter | Short | Required | Default | Description |
|-----------|-------|----------|---------|-------------|
| `--input` | `-i` | Yes | — | Folder containing images and PDFs |
| `--output` | `-o` | No | `r10n-output/video/asset-video.mp4` | MP4 file to create |
| `--order` | — | No | All assets | Slide order and PDF pages |
| `--duration` | `-d` | No | `0.5` | Seconds each slide is visible |
| `--fps` | — | No | `30` | Frames per second, 1–60 |
| `--aspect` | — | No | `16:9` | `9:16`, `1:1`, `4:5`, or `16:9` |
| `--size` | — | No | — | Custom `WIDTHxHEIGHT`; overrides aspect |
| `--fit` | — | No | `contain` | `contain` or `cover` |
| `--background` | `-b` | No | `#ffffff` | Background color for contain mode |
| `--fade` | — | No | `0.0` | Crossfade seconds between slides |
| `--crf` | — | No | `18` | H.264 quality; lower is better |
| `--recursive` | `-r` | No | `false` | Include files in subfolders |
| `--yes` | `-y` | No | `false` | Skip the final confirmation |

## Examples

Portrait reel:

```bash
r10n video --input ./export --aspect 9:16 --yes
```

Square feed video that fills the frame:

```bash
r10n video \
  --input ./assets \
  --aspect 1:1 \
  --fit cover \
  --background "#0f0f0f" \
  --fade 0.1 \
  --yes
```

Custom size:

```bash
r10n video --input ./assets --size 1920x1080 --order "1;2;3" --yes
```

Include subfolders:

```bash
r10n video --input ./campaign --recursive --yes
```

## Input

Supported images: PNG, JPG/JPEG, WebP, GIF (first frame), BMP, and TIFF.
PDFs are rendered page by page. Hidden files and folders are ignored.

Files are read from the input folder root unless `--recursive` is set.

## Output

- Format: MP4, H.264, `yuv420p`, `faststart`
- Default: 1920x1080 at 30fps, 0.5 seconds per slide
- Default path: `r10n-output/video/asset-video.mp4`
- Artifacts: the completed MP4 path is reported to the native UI and JSON stream

Preset sizes:

| `--aspect` | Resolution |
|------------|------------|
| `16:9` | 1920x1080 |
| `9:16` | 1080x1920 |
| `1:1` | 1080x1080 |
| `4:5` | 1080x1350 |

With `contain`, the whole image or PDF page stays visible over the background
color. With `cover`, the asset is scaled and center-cropped to fill the frame.

## Troubleshooting

**`ffmpeg is required but could not be installed automatically`:** r10n first
looks for ffmpeg on your system and then tries your package manager. If that
fails, run the install command printed in the error once and rerun the
automation.

**`Video width and height must be even`:** H.264 `yuv420p` requires even
dimensions. Use `1080x1350`, not `1081x1351`.

**PDF pages are cropped:** `--fit cover` intentionally crops. Use the default
`--fit contain` to keep every page edge visible.

**A PDF is not listed:** Check the folder path, or add `--recursive` when the
file is in a nested folder.

## See also

- [Images](images.md)
- [Fill PDFs](fill-pdfs.md)
- [Markdown to PDF](markdown-to-pdf.md)
