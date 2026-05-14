# logslice

A fast command-line utility for extracting time-bounded slices from large log files without loading them fully into memory.

---

## Installation

```bash
pip install logslice
```

Or install from source:

```bash
git clone https://github.com/yourname/logslice.git && cd logslice && pip install .
```

---

## Usage

```bash
logslice --start "2024-01-15 08:00:00" --end "2024-01-15 09:00:00" app.log
```

Pipe the output or save it to a file:

```bash
logslice --start "2024-01-15 08:00:00" --end "2024-01-15 09:00:00" app.log > slice.log
```

### Options

| Flag | Description |
|------|-------------|
| `--start` | Start of the time range (inclusive) |
| `--end` | End of the time range (inclusive) |
| `--format` | Custom timestamp format (default: auto-detect) |
| `--output` | Write output to a file instead of stdout |

### Example

```bash
logslice --start "2024-01-15 08:00:00" --end "2024-01-15 08:05:00" /var/log/nginx/access.log
```

logslice uses binary search to locate the start position, so it never loads the entire file into memory — making it suitable for multi-gigabyte log files.

---

## Requirements

- Python 3.8+

---

## License

This project is licensed under the [MIT License](LICENSE).