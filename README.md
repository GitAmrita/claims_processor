# claims_processor

## Getting Started

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Project

Run the main script to process claims:

```bash
python main.py
```

This will:
- Read claims from `sample_data/input_claims.csv` (default)
- Process them using parallel processing (configurable via `config.py`)
- Write results to `sample_data/output_claims.json`
- Generate a summary in `sample_data/output_summary.json`

#### Input Files

The project includes three sample input files:

1. **`sample_data/input_claims.csv`** (26 rows)
   - Small dataset for quick testing and validation
   - Demonstrates various validation scenarios (see "Sample Claim Validation Results" section below)
   - Used by default when running `python main.py`
   - **Processing time:** ~0.8 seconds (with parallel processing enabled)

2. **`sample_data/big_input_claims.csv`** (5,000 rows)
   - Large dataset for performance testing at scale
   - Useful for benchmarking parallel processing performance
   - To use this file, modify `INPUT_FILE` in `main.py`:
     ```python
     INPUT_FILE = Path("sample_data/big_input_claims.csv")
     ```
   - **Processing time:** ~1.77 seconds (with parallel processing enabled)

3. **`sample_data/very_big_input_claims.csv`** (50,000 rows)
   - Very large dataset for extensive performance and scaling testing
   - Contains mix of approved and rejected claims (~60% approved, ~40% rejected)
   - To use this file, modify `INPUT_FILE` in `main.py`:
     ```python
     INPUT_FILE = Path("sample_data/very_big_input_claims.csv")
     ```
   - **Processing time:** ~2.26 seconds (with parallel processing enabled)

### Configuration

Edit `claims_processor/config.py` to configure behavior:

- `USE_PARALLEL`: Set to `False` for sequential processing (useful for debugging)
- `VALIDATE_NDC_ONLINE`: Set to `False` to skip online NDC validation

### Running Tests

#### Run All Tests

```bash
pytest tests/
```

#### Run a Specific Test File

```bash
pytest tests/test_processor.py
```

#### Run a Specific Test Class

```bash
pytest tests/test_processor.py::TestProcessClaim
```

#### Run a Specific Test

```bash
pytest tests/test_processor.py::TestProcessClaim::test_process_claim_approved
```

#### Verbose Output

For more detailed test output:

```bash
pytest -v          # Verbose: shows each test name
pytest -vv         # Very verbose: shows more details
```

## Architecture

### High-Level Overview

The claims processor uses a parallel processing architecture optimized for handling large CSV files efficiently. The system processes claims in chunks using multiple worker processes, with asynchronous batch validation of NDC codes to minimize I/O bottlenecks.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Main Entry Point                              │
│                              (main.py)                                   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    process_claims_parallel()                            │
│                    (claims_processor/io.py)                             │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Configuration (config.py)                                       │  │
│  │ • USE_PARALLEL: Enable/disable parallel processing              │  │
│  │ • VALIDATE_NDC_ONLINE: Enable/disable online NDC validation    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Sequential Mode (use_parallel=False)                            │  │
│  │ ┌──────────────┐                                               │  │
│  │ │ Read Chunks  │──► Process Chunk ──► Process Chunk ──► ...  │  │
│  │ └──────────────┘                                               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Parallel Mode (use_parallel=True)                              │  │
│  │                                                                 │  │
│  │  ProcessPoolExecutor (num_workers = CPU count)                  │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │  │ Worker N │      │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │  │
│  │       │             │             │             │             │  │
│  │       └─────────────┴─────────────┴─────────────┘             │  │
│  │                    │                                             │  │
│  │                    ▼                                             │  │
│  │         _process_chunk_with_ndc_cache()                         │  │
│  │         (Each worker processes one chunk)                       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              _process_chunk_with_ndc_cache()                            │
│              (Per-Chunk Processing)                                     │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Step 1: Extract Unique NDCs                                    │  │
│  │   {claim.ndc for claim in claims_chunk if claim.ndc}            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                │                                         │
│                                ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Step 2: Batch Async NDC Validation                              │  │
│  │   validate_ndcs_batch_async(ndcs)                               │  │
│  │                                                                 │  │
│  │   ┌──────────────────────────────────────────────────────────┐ │  │
│  │   │ Per-Process Cache (_ndc_cache)                          │ │  │
│  │   │ • Check cache first                                      │ │  │
│  │   │ • Only validate uncached NDCs                            │ │  │
│  │   └──────────────────────────────────────────────────────────┘ │  │
│  │                                                                 │  │
│  │   ┌──────────────────────────────────────────────────────────┐ │  │
│  │   │ Concurrent HTTP Requests (aiohttp)                      │ │  │
│  │   │ • Semaphore limit: MAX_CONCURRENT_NDC_REQUESTS (200)     │ │  │
│  │   │ • Async validation: _validate_single_ndc_async()         │ │  │
│  │   │ • FDA API: https://api.fda.gov/drug/ndc.json            │ │  │
│  │   └──────────────────────────────────────────────────────────┘ │  │
│  │                                                                 │  │
│  │   Returns: Dict[str, bool] (NDC -> validation result)        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                │                                         │
│                                ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Step 3: Process Claims Serially                                │  │
│  │   for claim in claims_chunk:                                    │  │
│  │     process_claim(claim, ndc_cache=ndc_cache)                  │  │
│  │                                                                 │  │
│  │   ┌──────────────────────────────────────────────────────────┐ │  │
│  │   │ process_claim() (claims_processor/processor.py)         │ │  │
│  │   │ 1. validate_claim()                                     │ │  │
│  │   │    • Required fields validation                          │ │  │
│  │   │    • Format & value validation                           │ │  │
│  │   │    • NDC validation (uses cache)                        │ │  │
│  │   │ 2. Business rules                                        │ │  │
│  │   │    • Max pills per day check                             │ │  │
│  │   │ 3. calculate_copay()                                    │ │  │
│  │   │    • Plan-specific copay calculation                     │ │  │
│  │   │ 4. Return ProcessedClaim                                │ │  │
│  │   └──────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  Returns: List[ProcessedClaim]                                         │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Output Generation                                 │
│                                                                         │
│  ┌──────────────────────────┐  ┌──────────────────────────┐         │
│  │ write_processed_claims()  │  │ write_processing_summary()│         │
│  │ • output_claims.json      │  │ • output_summary.json     │         │
│  └──────────────────────────┘  └──────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. **CSV Reading** (`read_claims_csv_chunks`)
- Memory-safe chunked reading
- Streams data one chunk at a time
- Configurable chunk size (default: 1000 claims)

#### 2. **Parallel Processing** (`process_claims_parallel`)
- Uses `ProcessPoolExecutor` for true parallelism 
- Number of workers defaults to CPU count
- Can be disabled via `USE_PARALLEL` config for debugging
- Each worker process handles one chunk independently

#### 3. **NDC Validation** (`validate_ndcs_batch_async`)
- **Bottleneck Optimization**: Identified as the primary bottleneck (HTTP I/O)
- **Batch Processing**: Validates all NDCs in a chunk concurrently
- **Async I/O**: Uses `aiohttp` for non-blocking HTTP requests
- **Concurrency Control**: Semaphore limits to 200 concurrent requests
- **Caching**: Per-process cache (`_ndc_cache`) to avoid duplicate API calls
- **FDA API**: Validates against `https://api.fda.gov/drug/ndc.json`

#### 4. **Claim Processing** (`process_claim`)
- Validates claim data (format, values, required fields)
- Applies business rules (max pills per day, etc.)
- Calculates copay based on plan type
- Returns `ProcessedClaim` with status (APPROVED/REJECT)

#### 5. **Configuration** (`config.py`)
- Centralized configuration settings
- `USE_PARALLEL`: Enable/disable parallel processing
- `VALIDATE_NDC_ONLINE`: Enable/disable online NDC validation
- Can be overridden via function parameters

### Performance Characteristics

- **I/O Bound**: CSV reading is sequential but fast
- **CPU Bound**: Claim processing is parallelized via multiprocessing
- **Network Bound**: NDC validation is the bottleneck, optimized with:
  - Batch async validation (all NDCs in chunk validated concurrently)
  - Per-process caching (avoid duplicate API calls)
  - Semaphore-controlled concurrency (prevent API rate limiting)

### Performance & Scaling

The following table shows performance benchmarks across different dataset sizes, demonstrating the system's scalability:

| Dataset Size | File | Processing Time | Throughput |
|-------------|------|----------------|------------|
| 26 rows | `input_claims.csv` | ~0.8 seconds | ~33 claims/sec |
| 5,000 rows | `big_input_claims.csv` | ~1.77 seconds | ~2,825 claims/sec |
| 50,000 rows | `very_big_input_claims.csv` | ~2.26 seconds | ~22,124 claims/sec |

**Key Observations:**
- **Near-linear scaling**: Processing time increases sub-linearly with dataset size, demonstrating efficient parallelization
- **Throughput improvement**: Larger datasets achieve significantly higher throughput due to better parallelization efficiency
- **Bottleneck**: NDC validation (network I/O) remains the primary bottleneck, but async batch processing minimizes its impact
- **Configuration**: All tests performed with:
  - Parallel processing enabled (`USE_PARALLEL = True`)
  - Online NDC validation enabled (`VALIDATE_NDC_ONLINE = True`)
  - 8 worker processes (CPU count)
  - Chunk size: 1,000 claims


### Data Flow

1. **Input**: CSV file with claims data
2. **Chunking**: File is read in configurable chunks (default: 1000 claims)
3. **Parallel Distribution**: Chunks are distributed to worker processes
4. **Per-Chunk Processing**:
   - Extract unique NDCs from chunk
   - Batch validate NDCs asynchronously (concurrent HTTP requests)
   - Process each claim serially using NDC cache
5. **Aggregation**: Results from all workers are collected
6. **Output**: JSON files with processed claims and summary statistics

### Concurrency Model

- **Inter-Chunk Parallelism**: `ProcessPoolExecutor` (multiple processes)
- **Intra-Chunk Parallelism**: `asyncio` + `aiohttp` (async HTTP requests)
- **Serial Processing**: Individual claim processing within chunks (fast enough)

This hybrid approach maximizes performance by:
- Using processes for CPU-bound work (claim processing)
- Using async I/O for network-bound work (NDC validation)
- Batching network requests to minimize latency

## Sample Claim Validation Results

The table below lists which claims fail which validations according to the business rules for the **`input_claims.csv`** file (26 rows). This demonstrates various validation scenarios including passing claims, format errors, business rule violations, and missing fields.

| Claim ID | Failing Validations |
|----------|-------------------|
| CLM001 | ✅ Passes all |
| CLM002 | ✅ Passes all |
| CLM003 | ✅ Passes all |
| CLM004 | member_id invalid, ndc fails OpenFDA |
| CLM005 | quantity = 0 |
| CLM006 | days_supply = 100 |
| CLM007 | quantity = -5, days_supply = 0 |
| CLM008 | drug_cost = 0 |
| CLM009 | date_of_service future, drug_cost = -20 |
| CLM010 | ndc fails OpenFDA |
| CLM011 | ndc fails OpenFDA |
| CLM012 | ✅ Passes all |
| CLM013 | Too many pills |
| CLM014 | Too many pills|
| CLM015 | member_id invalid, ndc fails OpenFDA |
| CLM016 | ndc invalid length, date_of_service future |
| CLM017 | drug_cost = 0 |
| CLM018 | date_of_service future, days_supply = 0 |
| CLM019 | Too many pills |
| CLM020 | ✅ Passes all |
| CLM021 | member_id missing |
| CLM022 | ndc missing |
| CLM023 | date_of_service missing |
| CLM024 | days_supply missing |
| CLM025 | drug_cost missing |
| CLM026 | plan_type missing, ndc fails OpenFDA |

## Error Distribution Histogram

The following histogram shows the frequency of each validation error type found in the processed claims from **`input_claims.csv`** (26 rows). This visualization helps identify the most common validation failures:

| Error Type | Count | Histogram |
|-----------|-------|-----------|
| ndc is not a valid FDA NDC | 7 | ██████████████████████████████████████████████████ |
| days_supply must be between 1 and 90 | 3 | █████████████████████ |
| drug_cost must be positive | 3 | █████████████████████ |
| Too many pills per day | 3 | █████████████████████ |
| member_id must be exactly 10 digits | 2 | ██████████████ |
| quantity must be positive | 2 | ██████████████ |
| ndc must be exactly 11 digits | 2 | ██████████████ |
| date_of_service cannot be in the future | 1 | ███████ |
| member_id is required | 1 | ███████ |
| ndc is required | 1 | ███████ |
| date_of_service is required | 1 | ███████ |
| days_supply is required | 1 | ███████ |
| drug_cost is required | 1 | ███████ |
| plan_type is required | 1 | ███████ |

**Summary:**
- **Total Errors:** 29
- **Unique Error Types:** 14
- **Claims with Errors:** 21

