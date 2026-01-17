import csv
import json
import asyncio
from typing import Iterator, List, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

from .model import Claim, ProcessedClaim, ProcessingSummary
from .enums import Status
from .utils import parse_date, parse_int, parse_decimal, parse_plan_type


REQUIRED_COLUMNS = {
    "claim_id",
    "member_id",
    "ndc",
    "date_of_service",
    "quantity",
    "days_supply",
    "drug_cost",
    "plan_type",
}


def read_claims_csv_chunks(file_path: str, chunk_size: int = 1000) -> Iterator[List[Claim]]:
    """
    Read CSV file in chunks for parallel processing.
    
    Args:
        file_path: Path to CSV file
        chunk_size: Number of rows per chunk
        
    Yields:
        Lists of Claim objects (chunks)
    """
    chunk = []
    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        
        _validate_headers(reader.fieldnames)
        
        for row in reader:
            claim = _parse_row(row)
            chunk.append(claim)
            
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        
        # Yield remaining claims
        if chunk:
            yield chunk

def _parse_row(row: dict) -> Claim:
    """Parse a CSV row into a Claim object, handling missing values gracefully."""
    # Get values with defaults for missing keys, strip whitespace
    claim_id = row.get("claim_id", "").strip()
    member_id = row.get("member_id", "").strip() or None
    ndc = row.get("ndc", "").strip() or None
    date_of_service = parse_date(row.get("date_of_service", "").strip())
    quantity = parse_int(row.get("quantity", "").strip())
    days_supply = parse_int(row.get("days_supply", "").strip())
    drug_cost = parse_decimal(row.get("drug_cost", "").strip())
    plan_type = parse_plan_type(row.get("plan_type", "").strip())
    
    return Claim(
        claim_id=claim_id,
        member_id=member_id,
        ndc=ndc,
        date_of_service=date_of_service,
        quantity=quantity,
        days_supply=days_supply,
        drug_cost=drug_cost,
        plan_type=plan_type,
    )

def _validate_headers(headers: Optional[List[str]]) -> None:
    if not headers:
        raise ValueError("CSV file is missing headers")

    missing = REQUIRED_COLUMNS - set(headers)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

def serialize_processed_claim(claim: ProcessedClaim) -> dict:
    """
    Convert ProcessedClaim domain object to JSON-serializable dict.
    """
    return {
        "claim_id": claim.claim_id,
        "status": claim.status.value,
        "copay_amount": (
            float(claim.copay_amount)
            if claim.copay_amount is not None
            else None
        ),
        "rejection_reason": claim.rejection_reason,
        "processed_at": claim.processed_at.isoformat(),
    }

def write_processed_claims(
    claims: List[ProcessedClaim],
    output_path: str,
) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            [serialize_processed_claim(c) for c in claims],
            f,
            indent=2,
        )


def compute_processing_summary(
    claims: List[ProcessedClaim],
    processing_time_seconds: float,
) -> ProcessingSummary:
    """
    Compute processing summary statistics from processed claims.
    
    Args:
        claims: List of processed claims
        processing_time_seconds: Time taken to process all claims
    
    Returns:
        ProcessingSummary object with computed statistics
    """
    total_processed = len(claims)
    total_approved = sum(1 for claim in claims if claim.status == Status.APPROVED)
    total_rejected = sum(1 for claim in claims if claim.status == Status.REJECT)

    # Calculate percentages, handling division by zero
    percentage_approved = (
        round((total_approved / total_processed * 100), 2) if total_processed > 0 else 0.0
    )
    percentage_rejected = (
        round((total_rejected / total_processed * 100), 2) if total_processed > 0 else 0.0
    )

    return ProcessingSummary(
        total_rows_processed=total_processed,
        total_approved=total_approved,
        total_rejected=total_rejected,
        percentage_approved=percentage_approved,
        percentage_rejected=percentage_rejected,
        processing_time_seconds=round(processing_time_seconds, 2),
    )


def serialize_processing_summary(summary: ProcessingSummary) -> dict:
    """
    Convert ProcessingSummary domain object to JSON-serializable dict.
    """
    return {
        "total_rows_processed": summary.total_rows_processed,
        "total_approved": summary.total_approved,
        "total_rejected": summary.total_rejected,
        "percentage_approved": summary.percentage_approved,
        "percentage_rejected": summary.percentage_rejected,
        "processing_time_seconds": summary.processing_time_seconds,
    }


def write_processing_summary(
    claims: List[ProcessedClaim],
    summary_path: str,
    processing_time_seconds: float,
) -> None:
    """
    Compute and write processing summary statistics to a JSON file.
    
    Args:
        claims: List of processed claims
        summary_path: Path to write the summary JSON file
        processing_time_seconds: Time taken to process all claims
    """
    summary = compute_processing_summary(claims, processing_time_seconds)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(serialize_processing_summary(summary), f, indent=2)


def _process_chunk_with_ndc_cache(claims_chunk: List[Claim]) -> List[ProcessedClaim]:
    """
    Process a chunk of claims with async NDC validation.
    This function is designed to be called by worker processes.
    
    NDC validation is batched (all NDCs validated concurrently), but individual
    claim processing happens serially within each chunk. This is optimal since:
    - NDC validation was the bottleneck and is now batched
    - Other processing (validation, copay calculation) is fast
    - Chunks are already processed in parallel via ProcessPoolExecutor
    
    Args:
        claims_chunk: List of Claim objects to process
        
    Returns:
        List of ProcessedClaim objects
    """
    from .processor import process_claim
    from .validators import validate_ndcs_batch_async
    
    # Extract unique NDCs that need validation
    ndcs_to_validate = {claim.ndc for claim in claims_chunk if claim.ndc}
    
    # Validate NDCs asynchronously (batch validation - all NDCs concurrently)
    if ndcs_to_validate:
        ndc_cache = asyncio.run(validate_ndcs_batch_async(ndcs_to_validate))
    else:
        ndc_cache = {}
    
    # Process each claim serially using the NDC cache
    # (Serial is fine here since NDC validation bottleneck is already batched)
    processed_claims = []
    for claim in claims_chunk:
        result = process_claim(claim, ndc_cache=ndc_cache)
        processed_claims.append(result)
    
    return processed_claims


def process_claims_parallel(
    file_path: str,
    num_workers: Optional[int] = None,
    chunk_size: int = 1000,
) -> List[ProcessedClaim]:
    """
    Process claims in parallel using multiprocessing with async NDC validation.
    
    Args:
        file_path: Path to CSV file
        num_workers: Number of worker processes (defaults to CPU count)
        chunk_size: Number of claims per chunk
        
    Returns:
        List of ProcessedClaim objects
    """
    import multiprocessing
    
    if num_workers is None:
        num_workers = multiprocessing.cpu_count()
        print(f"Using {num_workers} worker processes")
    
    all_processed_claims = []
    
    # Process chunks in parallel
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Submit all chunks for processing
        future_to_chunk = {}
        for chunk in read_claims_csv_chunks(file_path, chunk_size):
            future = executor.submit(_process_chunk_with_ndc_cache, chunk)
            future_to_chunk[future] = chunk
        
        # Collect results as they complete
        for future in as_completed(future_to_chunk):
            try:
                processed_chunk = future.result()
                all_processed_claims.extend(processed_chunk)
            except Exception as exc:
                chunk = future_to_chunk[future]
                print(f"Chunk processing failed: {exc}")
                # Optionally: process chunk synchronously as fallback
                raise
    
    return all_processed_claims

