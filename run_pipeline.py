#!/usr/bin/env python3
"""
CLI entrypoint to execute the Baseline V1 Industrial Fire AI Pipeline.
Usage:
    python run_pipeline.py
    python run_pipeline.py --config config/default_config.yaml --zip path/to/firms.zip
"""

import sys
import argparse
from pathlib import Path

# Add project root to Python sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.pipeline import run_pipeline

def main():
    parser = argparse.ArgumentParser(
        description="Run Baseline V1 Industrial Fire AI Pipeline"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to YAML configuration file (default: config/default_config.yaml)"
    )
    parser.add_argument(
        "--zip",
        type=str,
        default=None,
        help="Path to NASA FIRMS ZIP archive (optional override)"
    )

    args = parser.parse_args()
    run_pipeline(config_path=args.config, custom_firms_zip=args.zip)

if __name__ == "__main__":
    main()
