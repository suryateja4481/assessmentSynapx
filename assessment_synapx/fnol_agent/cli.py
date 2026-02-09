import sys
import json
import argparse
from .extractor import read_pdf_text, extract_fields, extract_from_file
from .router import build_output


def main(argv=None):
    # Use argparse to make argument handling explicit — if the user does not supply
    # the required positional `path` argument, argparse will print usage and exit
    # without generating any JSON output.
    parser = argparse.ArgumentParser(description="FNOL extraction, validation & routing CLI")
    parser.add_argument("path", nargs=1, help="Path to FNOL PDF file")
    parser.add_argument("--expected", required=False, help="Path to JSONL file with expected values (one JSON object per line)")
    parser.add_argument("--output", required=False, help="Path to save output JSON file")
    parser.add_argument("--debug", action="store_true", help="Print debug info")
    args = parser.parse_args(argv[1:] if argv is not None else None)

    path = args.path[0]
    expected_path = args.expected
    try:
        if expected_path:
            # Run validation which will extract, compare to expected JSONL and produce reasoning
            from .validator import validate

            out = validate(expected_path, path)
        else:
            # Extract and route; then call LLM for concise reasoning
            from .extractor import extract_from_file
            from .router import build_output
            from .validator import call_llm_reasoning

            extracted = extract_from_file(path)
            # remove raw text content before routing/output; retain length
            raw_text = None
            if isinstance(extracted, dict) and "_raw_text" in extracted:
                raw_text = extracted.pop("_raw_text")
            out = build_output(extracted)

            # Build prompts for reasoning
            system_prompt = (
                "You are an insurance claim assistant. Given extracted fields from a FNOL form,"
                " produce a concise explanation (2-4 sentences) for the routing decision and note any"
                " missing or suspicious fields."
            )
            user_prompt = (
                f"Extracted fields: {json.dumps(extracted, indent=2)}\n"
                f"Missing fields: {out.get('missingFields')}\n"
                f"Recommended route: {out.get('recommendedRoute')}\n"
                f"Raw text length: {len(raw_text) if raw_text else 0}\n"
                "Provide a short reasoning for the routing decision and any suggested next steps."
            )

            # validator.call_llm_reasoning currently expects a single user_prompt argument
            # (it builds the system prompt internally), so pass user_prompt only.
            reasoning = call_llm_reasoning(user_prompt)
            out["reasoning"] = reasoning
    except Exception as e:
        print(json.dumps({"error": f"Failed to validate: {e}"}))
        sys.exit(2)
    if args.debug:
        raw_len = out.get("raw_text_length") if isinstance(out, dict) else None
        print(json.dumps({"debug": {"raw_text_length": raw_len if raw_len is not None else 0}}))
    
    output_json = json.dumps(out, indent=2)
    print(output_json)
    
    # Save to file if output path is specified
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_json)
            print(f"Output saved to {args.output}", file=sys.stderr)
        except Exception as e:
            print(json.dumps({"error": f"Failed to save output file: {e}"}), file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
