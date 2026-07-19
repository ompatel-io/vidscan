# VidScan CLI Changelog

## [1.0.0] - 2026-07-19

**Requires Python 3.10+**

> For Python 3.7–3.9, use [0.9.0](#090---2026-04-29).

### Added

- Natural sorting for file and folder names, used by default
- `--output-dir` option to specify path for report output, useful when write permission is not present and for flexibility

### Changed

- Raise min Python version to 3.10

- Sorting by folders and videos independently
  - Change old sort options: `--sort-by`, `--sort-order` to `--sort-folders`, `--sort-videos`
  - Take sort order optionally with sort criteria, e.g. `duration:desc`

- Report options
  - Replace `--format` and `--template` with single `--report` option
  - Report types: `txt-summary`, `txt-detailed`, `csv`, `json`, or `all` to generate all at once

- Text reports
  - Remove size from `txt-summary`
  - Add size by default in `txt-detailed`
  - Show full paths instead of folder names in `txt-detailed`
  - Change default report type to `txt-detailed`

- Rename output report filenames
- Raise `ArgumentTypeError` for invalid `--workers` value instead of fallback to default

### Fixed

- Provide custom error messages if non numeric duration (such as `N/A`) returned by ffprobe
- Update script entrypoint in pyproject toml

### Internal

- Python 3.10+
  - `slots=True` in dataclasses instead of manual `__slots__`
  - Newer type hinting syntax
  - Remove manual `cancel_futures` fallback for older versions

- Refactor single file to dedicated modules and package
- Use TypedDict for json structure
- Sort ScanResult DTO directly and pass to report generators

## [0.9.0] - 2026-04-29

**Last release supporting Python 3.7+**

**Pin with `pip install vidscan==0.9.0`**

**Initial PyPI release.**
