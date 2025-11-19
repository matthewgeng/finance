# finance
## Chase Statement Parser

A small command-line tool that extracts transactions from **Chase PDF credit card statements** and exports them as CSV files.  
Parsing is powered by **Camelot**, **pypdf**, and **pandas**.

---

## Features

- Automatically detects the number of pages in a statement  
- Extracts transaction tables from all pages except the last (which contains no transactions)  
- Handles the special layout of the first transaction page vs. subsequent pages  
- Outputs a clean CSV file into a `parsed/` directory next to the PDF  
- CLI interface for easy use

---

## Requirements

Python 3.9+ recommended.

Install dependencies:

```bash
pip install camelot-py pypdf pandas
```

> **Note:** Camelot requires Ghostscript installed on your system.  
> macOS (Homebrew):
>
> ```bash
> brew install ghostscript
> ```

---

## Usage

Run the parser:

```bash
python cli.py /path/to/ChaseStatement.pdf
```

### Optional Flags

- `--first-page`  
  Override the assumed index of the first transaction page:

  ```bash
  python cli.py statement.pdf --first-page 4
  ```

- `--verbose`  
  Enable extra debugging output:

  ```bash
  python cli.py statement.pdf --verbose
  ```

- Both flags can be combined:

  ```bash
  python cli.py statement.pdf --first-page 4 --verbose
  ```

---

## Output

If your statement is:

```
/Users/me/statements/Jan2025.pdf
```

The parsed CSV will be saved to:

```
/Users/me/statements/parsed/Jan2025.csv
```

---

## Troubleshooting

### Camelot returns no tables
This usually means the PDF layout differs from expected.  
Try adjusting `table_areas`, `columns`, or `row_tol` inside `statement.py`.