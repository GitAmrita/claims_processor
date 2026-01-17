import time
from pathlib import Path
from claims_processor.io import (
    process_claims_parallel,
    write_processed_claims,
    write_processing_summary,
)

# Input CSV and output JSON paths
INPUT_FILE = Path("sample_data/input_claims.csv")
OUTPUT_FILE = Path("sample_data/output_claims.json")
SUMMARY_FILE = Path("sample_data/output_summary.json")


def main() -> None:
    """
    Test run for the claims processor.
    Uses parallel processing with async NDC validation for optimal performance.
    """
    start_time = time.time()
    # Process claims in parallel with async NDC validation
    # Uses ProcessPoolExecutor for CPU-bound work and async HTTP for NDC validation
    # use_parallel and chunk_size parameters default to config values if not provided
    processed_claims = process_claims_parallel(
        str(INPUT_FILE),
        num_workers=None,  # Uses CPU count by default
    )

    # Write processed claims to JSON
    write_processed_claims(processed_claims, OUTPUT_FILE)

    # Calculate elapsed time
    elapsed_time = time.time() - start_time

    # Write summary
    write_processing_summary(processed_claims, SUMMARY_FILE, elapsed_time)

    # Print results
    print(f"Processed {len(processed_claims)} claims in {elapsed_time:.2f} seconds")
    print(f"Output file written to {OUTPUT_FILE}")
    print(f"Summary file written to {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
