# Installation & Setup

Prerequisites
- Python 3.8 or later
- pip

Quick setup (Windows PowerShell)

```powershell
python -m venv .venv
. .venv\Scripts\Activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Quick setup (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the agent

- Run using the repository entry point:

```bash
python main.py path/to/fnol.pdf
```

- Or call the CLI module directly (useful for flags):

```bash
python -m fnol_agent.cli path/to/fnol.pdf --output outputs/output.json --debug
```

CLI flags
- `--output PATH` : save output JSON to `PATH`
- `--expected PATH` : path to a JSONL file containing expected field values (one JSON object per line) for validation
- `--debug` : print debug information

Expected JSONL for validation
- Provide one JSON object per line. Each object should represent expected extracted fields for a given PDF.

Troubleshooting
- If permission errors occur activating the venv on PowerShell, run: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` as admin.
- If `pip install` fails, try upgrading pip: `python -m pip install --upgrade pip`.

If you want, I can also add a short example `expected.jsonl` and a sample PDF placeholder to `outputs/` for testing.
