# Legacy Code

This directory contains code that is no longer used in the main codebase but has been preserved for reference.

## Contents

### DAGAnalyzer.py
- **Original location**: `py_dpm/semantics/DAG/DAGAnalyzer.py`
- **Purpose**: Generates Directed Acyclic Graphs from calculation scripts
- **Status**: Not integrated into the public API
- **Reason for removal**: Not imported anywhere in production code
- **Notes**: May be useful for future scripting validation features

### external_validations/Utils.py
- **Original location**: `py_dpm/ValidationsGeneration/Utils.py`
- **Purpose**: Process external EBA validation rules from Excel files
- **Status**: Contains known issues (see TODO: "this does not work because DDL restrictions")
- **Reason for removal**: References non-existent paths, appears to be incomplete/broken
- **Notes**: Only used by `ValidationsGenerationUtils.py` in one function. May need to be reimplemented if external validation rules feature is needed.

## Recovery

If any of this code needs to be restored:

1. Check git history for the complete version with all dependencies
2. Review and update imports to match current structure
3. Add tests before reintegrating
4. Update API documentation

## Deletion

This directory can be safely deleted if:
- No plans to revive these features exist
- Git history is sufficient for reference
- Team consensus agrees code won't be needed
