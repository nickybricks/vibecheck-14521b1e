"""Pipeline jobs for scheduled data ingestion.

Jobs handle retry logic, error recovery, and execution tracking for:
- News article polling (15 min frequency)
- Story cluster polling (60 min frequency)
"""
