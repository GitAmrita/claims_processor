from pathlib import Path
from claims_processor.io import read_claims_csv, write_processed_claims
from claims_processor.processor import process_claim

# Input CSV and output JSON paths
INPUT_FILE = Path("sample_data/input_claims.csv")
OUTPUT_FILE = Path("sample_data/output_claims.json")


def main() -> None:
    """
    Test run for the claims processor.
    Reads CSV → processes each claim → writes JSON output.
    """
    processed_claims = []

    # Memory-safe streaming read
    for claim in read_claims_csv(INPUT_FILE):
        result = process_claim(claim)
        processed_claims.append(result)

    # Write processed claims to JSON
    write_processed_claims(processed_claims, OUTPUT_FILE)

    print(f"Processed {len(processed_claims)} claims.")
    print(f"Output written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
