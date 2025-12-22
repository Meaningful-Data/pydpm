# pyDPM Project Context & Instructions

## Strategic Objective
**pyDPM** is designed to be a comprehensive, open-source **Data Point Model (DPM)** library. While its current implementation focuses heavily on **DPM-XL** (Data Point Model eXtensible Language), its strategic goal is to serve as a general-purpose toolkit for all DPM-related operations.

The library aims to facilitate not just the processing of DPM-XL expressions, but also the broader **exploration, querying, and understanding of DPM structures** (e.g., identifying which items belong to a specific property, analyzing hierarchies, and managing metadata).

## Core Capabilities & Vision

### 1. DPM-XL Processing (Current Core)
*   **Syntax & Semantics**: Robust parsing and semantic validation of DPM-XL expressions (e.g., `{tC_01.00, r0100, c0010}`).
*   **Validation Rules**: Enforcing data type correctness, operand validity, and structural integrity.

### 2. DPM Querying & Exploration (Expanding Scope)
*   **Metadata Analysis**: Tools to query and understand the relationships within the DPM.
    *   *Example*: "What items are associated with Property X?"
    *   *Example*: "Retrieve the hierarchy of table Y."
*   **Structural Navigation**: functions to traverse the complex web of Dimensions, Domains, and Members.

### 3. Data Management & Migration
*   **Database Migration**: Converting legacy DPM storage formats (MS Access) into modern, queryable schemas (SQLite).
*   **Data Dictionary Validation**: Ensuring the consistency of the underlying metadata (tables, rows, columns).

## Code Organization
The codebase matches this evolving scope with a modular structure:

*   **`py_dpm/api/`**: Public interfaces. currently dominated by `SyntaxAPI` and `SemanticAPI` (DPM-XL focused), but ready to expand with `QueryAPI` or `ExplorerAPI`.
*   **`py_dpm/models.py` & `py_dpm/views/`**: The backbone of the DPM data structure. This ORM layer allows for complex querying of concepts, hierarchies, and relationships, supporting the broader "DPM Exploration" goal.
*   **`py_dpm/grammar/`**: ANTLR4 definitions for DPM-XL.
*   **`py_dpm/migration.py`**: Bridges the gap between old and new formats.

## Instructions for Future Development
When working on this codebase, always consider the **General DPM Context**:
*   **Extensibility**: Design features that can apply to general DPM concepts, not just the specific implementation details of DPM-XL 1.0.
*   **Query-First**: Prioritize capabilities that help users ask questions about their data model (introspection).
*   **Independence**: While DPM-XL is a major use case, keep the core DPM data structures (Dimensions, Properties, Members) clean and potentially reusable for other DPM serialization formats if needed.
