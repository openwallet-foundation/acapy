# LTS Version Configuration

This file controls which version patterns are treated as Long Term Support (LTS) releases.

## How it works

When a release is published, the LTS workflow automatically:
1. Checks if the release version (major.minor) is listed in this file
2. If it matches, creates an LTS tag and GitHub release
3. Tags the published container images with the LTS tag

## Format

- One version pattern per line in `major.minor` format (e.g., `1.2` for versions 1.2.x)
- Lines starting with `#` are comments and will be ignored
- Empty lines are ignored

## Example

To enable LTS for versions 0.11.x and 1.0.x, add:
```
0.11
1.0
```

## Adding a new LTS version

1. Edit `.github/lts-versions.txt`
2. Add the major.minor version pattern (e.g., `1.3`)
3. Commit and push the changes
4. Future releases matching that pattern (e.g., `1.3.0`, `1.3.1`, etc.) will automatically be tagged as LTS

## Behavior

- For release `1.2.3` with `1.2` in this file:
  - Creates git tag: `1.2-lts`
  - Creates GitHub release: `1.2-lts`
  - Tags images: `py3.12-1.2-lts`
  
- When `1.2.4` is released:
  - Moves `1.2-lts` tag to point to `1.2.4`
  - Updates the `1.2-lts` GitHub release
  - Re-tags images so `py3.12-1.2-lts` points to the `1.2.4` image

This ensures the LTS tag always points to the latest patch release for that major.minor version.
