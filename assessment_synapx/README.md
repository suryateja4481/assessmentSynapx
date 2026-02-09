# FNOL Extraction & Routing Agent

See the installation guide: [INSTALL.md](INSTALL.md)

This repository implements a lightweight FNOL (First Notice of Loss) extraction and routing agent. It provides:

- deterministic extraction heuristics for common FNOL fields (PDF form fields + text parsing)
- detection of missing or inconsistent fields (validator)
- a rules-based routing engine that selects a recommended route and a short reasoning string
- a CLI entrypoint for extraction, validation and saving JSON outputs

**Assessment Checklist (status)**
- **Problem Statement**: Extract fields, detect missing/inconsistent, classify & route — **Implemented**
- **Sample FNOL documents**: at least one sample provided — **Partially (filled_fnol.txt present, no sample PDFs included)**
- **Fields to Extract**: Policy, Incident, Parties, Asset, Other mandatory fields — **Implemented (see extractor labels)**
- **Routing Rules**: fast-track, manual review, investigation flag, specialist queue — **Implemented**
- **Output Format**: JSON with `extractedFields`, `missingFields`, `recommendedRoute`, `reasoning` — **Implemented**
- **Tools & Frameworks**: Python, PyPDF2, LangChain/OpenAI/Groq for optional LLM reasoning — **Documented in requirements.txt**

**Files of interest**
- [main.py](main.py): program entrypoint that calls the package CLI
- [INSTALL.md](INSTALL.md): installation and run steps
- [fnol_agent/cli.py](fnol_agent/cli.py): CLI parsing and orchestration (`--expected`, `--output`, `--debug`)
- [fnol_agent/extractor.py](fnol_agent/extractor.py): PDF/text extraction heuristics and label mapping
- [fnol_agent/router.py](fnol_agent/router.py): mandatory-field checks and routing rules
- [fnol_agent/validator.py](fnol_agent/validator.py): compares extracted fields to expected JSONL and builds LLM prompt
- [fnol_agent/filled_fnol.txt](fnol_agent/filled_fnol.txt): example text FNOL
- [requirements.txt](requirements.txt): dependencies (PyPDF2, langchain, openai, groq)

**How it works (short)**
- Extraction: `extract_from_file()` first attempts PDF form field reads via PyPDF2; falls back to deterministic label/regex parsing on raw text.
- Validation: `validate()` loads one JSON object from a provided JSONL file and compares expected vs extracted values, returning `missing` and `inconsistent` lists.
- Routing: `build_output()` calls `find_missing()` and `route_and_reason()` to decide route according to the rules in the assessment brief.
- Reasoning: optional LLM call via LangChain (`call_llm_reasoning`) — requires API key(s) in environment (e.g. GROQ_API_KEY, GROQ_MODEL or OpenAI keys depending on your setup).

**Quick run examples**

Windows PowerShell (see full steps in INSTALL.md):

```powershell
python -m venv .venv
. .venv\Scripts\Activate
pip install -r requirements.txt
python main.py fnol_agent/filled_fnol.txt
```

Run validator with an expected JSONL file:

```powershell
python -m fnol_agent.cli fnol_agent/filled_fnol.txt --expected expected.jsonl --output outputs/output.json --debug
```


