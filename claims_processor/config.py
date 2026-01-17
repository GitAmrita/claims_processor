"""Configuration settings for claims processor."""

# Parallel processing configuration
USE_PARALLEL = True  # Set to False for sequential processing (useful for debugging)
CHUNK_SIZE = 1000  # Number of claims per chunk for parallel processing

# NDC validation configuration
VALIDATE_NDC_ONLINE = True  # Set to False to skip online NDC validation
