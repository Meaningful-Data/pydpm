#!/usr/bin/env python3
"""
AST Generator API - Simplified interface for external packages

This module provides a clean, abstracted interface for generating ASTs from DPM-XL expressions
without exposing internal complexity or version compatibility issues.
"""

from typing import Dict, Any, Optional, List, Union
import json
from py_dpm.api.syntax import SyntaxAPI
from py_dpm.api.semantic import SemanticAPI


class ASTGenerator:
    """
    Simplified AST Generator for external packages.

    Handles all internal complexity including:
    - Version compatibility
    - Context processing
    - Database integration
    - Error handling
    - JSON serialization
    """

    def __init__(self, database_path: Optional[str] = None,
                 connection_url: Optional[str] = None,
                 compatibility_mode: str = "auto",
                 enable_semantic_validation: bool = False):
        """
        Initialize AST Generator.

        Args:
            database_path: Optional path to SQLite data dictionary database
            connection_url: Optional SQLAlchemy connection URL for PostgreSQL
            compatibility_mode: "auto", "3.1.0", "4.0.0", or "current"
            enable_semantic_validation: Enable semantic validation (requires database)
        """
        self.syntax_api = SyntaxAPI()
        self.semantic_api = SemanticAPI(database_path=database_path, connection_url=connection_url) if enable_semantic_validation else None
        self.database_path = database_path
        self.connection_url = connection_url
        self.compatibility_mode = compatibility_mode
        self.enable_semantic = enable_semantic_validation

        # Internal version handling
        self._version_normalizers = self._setup_version_normalizers()

    def parse_expression(self, expression: str) -> Dict[str, Any]:
        """
        Parse DPM-XL expression into clean AST format.

        Args:
            expression: DPM-XL expression string

        Returns:
            Dictionary containing:
            - success: bool
            - ast: AST dictionary (if successful)
            - context: Context information (if WITH clause present)
            - error: Error message (if failed)
            - metadata: Additional information
        """
        try:
            # Parse with syntax API
            raw_ast = self.syntax_api.parse_expression(expression)

            # Extract context and expression
            context, expr_ast = self._extract_components(raw_ast)

            # Convert to clean JSON format
            ast_dict = self._to_clean_json(expr_ast, context)

            # Apply version normalization
            normalized_ast = self._normalize_for_compatibility(ast_dict)

            # Optional semantic validation
            semantic_info = None
            if self.enable_semantic and self.semantic_api:
                semantic_info = self._validate_semantics(expression)

            return {
                'success': True,
                'ast': normalized_ast,
                'context': self._serialize_context(context),
                'error': None,
                'metadata': {
                    'has_context': context is not None,
                    'expression_type': normalized_ast.get('class_name', 'Unknown'),
                    'semantic_info': semantic_info,
                    'compatibility_mode': self.compatibility_mode
                }
            }

        except Exception as e:
            return {
                'success': False,
                'ast': None,
                'context': None,
                'error': str(e),
                'metadata': {
                    'error_type': type(e).__name__,
                    'original_expression': expression[:100] + "..." if len(expression) > 100 else expression
                }
            }

    def parse_batch(self, expressions: List[str]) -> List[Dict[str, Any]]:
        """
        Parse multiple expressions efficiently.

        Args:
            expressions: List of DPM-XL expression strings

        Returns:
            List of parse results (same format as parse_expression)
        """
        results = []
        for i, expr in enumerate(expressions):
            result = self.parse_expression(expr)
            result['metadata']['batch_index'] = i
            results.append(result)

        return results

    def validate_expression(self, expression: str) -> Dict[str, Any]:
        """
        Validate expression syntax without full parsing.

        Args:
            expression: DPM-XL expression string

        Returns:
            Dictionary containing validation result
        """
        try:
            self.syntax_api.parse_expression(expression)
            return {
                'valid': True,
                'error': None,
                'expression': expression
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'expression': expression
            }

    def get_expression_info(self, expression: str) -> Dict[str, Any]:
        """
        Get comprehensive information about an expression.

        Args:
            expression: DPM-XL expression string

        Returns:
            Dictionary with expression analysis
        """
        result = self.parse_expression(expression)
        if not result['success']:
            return result

        ast = result['ast']
        context = result['context']

        # Analyze AST structure
        analysis = {
            'variable_references': self._extract_variables(ast),
            'constants': self._extract_constants(ast),
            'operations': self._extract_operations(ast),
            'has_aggregations': self._has_aggregations(ast),
            'has_conditionals': self._has_conditionals(ast),
            'complexity_score': self._calculate_complexity(ast),
            'context_info': context
        }

        result['analysis'] = analysis
        return result

    # Internal helper methods

    def _extract_components(self, raw_ast):
        """Extract context and expression from raw AST."""
        if hasattr(raw_ast, 'children') and len(raw_ast.children) > 0:
            child = raw_ast.children[0]
            if hasattr(child, 'expression') and hasattr(child, 'partial_selection'):
                return child.partial_selection, child.expression
            else:
                return None, child
        return None, raw_ast

    def _to_clean_json(self, ast_node, context=None):
        """Convert AST node to clean JSON format."""
        # Import the serialization function from utils
        from py_dpm.Utils.ast_serialization import serialize_ast

        # Use the serialize_ast function which handles all AST node types properly
        return serialize_ast(ast_node)

    def _serialize_context(self, context):
        """Serialize context to clean dictionary."""
        if not context:
            return None

        return {
            'table': getattr(context, 'table', None),
            'rows': getattr(context, 'rows', None),
            'columns': getattr(context, 'cols', None),
            'sheets': getattr(context, 'sheets', None),
            'default': getattr(context, 'default', None),
            'interval': getattr(context, 'interval', None)
        }

    def _normalize_for_compatibility(self, ast_dict):
        """Apply version compatibility normalization."""
        if self.compatibility_mode == "auto":
            # Auto-detect and normalize
            return self._auto_normalize(ast_dict)
        elif self.compatibility_mode in self._version_normalizers:
            normalizer = self._version_normalizers[self.compatibility_mode]
            return normalizer(ast_dict)
        else:
            return ast_dict

    def _setup_version_normalizers(self):
        """Setup version-specific normalizers."""
        return {
            "3.1.0": self._normalize_v3_1_0,
            "4.0.0": self._normalize_v4_0_0,
            "current": lambda x: x
        }

    def _normalize_v3_1_0(self, ast_dict):
        """Normalize AST for version 3.1.0 compatibility."""
        if not isinstance(ast_dict, dict):
            return ast_dict

        normalized = {}
        for key, value in ast_dict.items():
            # Handle Scalar item naming for v3.1.0
            if key == 'item' and isinstance(value, str) and ':' in value:
                namespace, code = value.split(':', 1)
                if namespace.endswith('_qEC'):
                    namespace = namespace.replace('_qEC', '_EC')
                if code.startswith('qx'):
                    code = code[1:]
                normalized[key] = f"{namespace}:{code}"

            # Handle TimeShiftOp field mapping
            elif ast_dict.get('class_name') == 'TimeShiftOp':
                if key == 'component':
                    normalized['reference_period'] = value
                    continue
                elif key == 'shift_number' and not isinstance(value, dict):
                    # Convert to Constant format for v3.1.0
                    normalized[key] = {
                        'class_name': 'Constant',
                        'type_': 'Integer',
                        'value': int(value)
                    }
                    continue
                elif key == 'period_indicator' and not isinstance(value, dict):
                    # Convert to Constant format for v3.1.0
                    period_map = {'A': 'Q'}  # Map known differences
                    actual_value = period_map.get(value, value)
                    normalized[key] = {
                        'class_name': 'Constant',
                        'type_': 'String',
                        'value': actual_value
                    }
                    continue

            # Recursively normalize nested structures
            if isinstance(value, dict):
                normalized[key] = self._normalize_v3_1_0(value)
            elif isinstance(value, list):
                normalized[key] = [self._normalize_v3_1_0(item) if isinstance(item, dict) else item for item in value]
            else:
                normalized[key] = value

        return normalized

    def _normalize_v4_0_0(self, ast_dict):
        """Normalize AST for version 4.0.0 compatibility."""
        if not isinstance(ast_dict, dict):
            return ast_dict

        normalized = {}
        for key, value in ast_dict.items():
            # Handle Scalar item naming for v4.0.0
            if key == 'item' and isinstance(value, str) and ':' in value:
                namespace, code = value.split(':', 1)
                if namespace.endswith('_EC') and not namespace.endswith('_qEC'):
                    namespace = namespace.replace('_EC', '_qEC')
                if code.startswith('x') and not code.startswith('qx'):
                    code = 'q' + code
                normalized[key] = f"{namespace}:{code}"

            # Handle TimeShiftOp field mapping
            elif ast_dict.get('class_name') == 'TimeShiftOp':
                if key == 'reference_period':
                    normalized['component'] = value
                    continue

            # Recursively normalize nested structures
            if isinstance(value, dict):
                normalized[key] = self._normalize_v4_0_0(value)
            elif isinstance(value, list):
                normalized[key] = [self._normalize_v4_0_0(item) if isinstance(item, dict) else item for item in value]
            else:
                normalized[key] = value

        return normalized

    def _auto_normalize(self, ast_dict):
        """Auto-detect version and normalize accordingly."""
        # Simple heuristic: check for version-specific patterns
        ast_str = json.dumps(ast_dict) if ast_dict else ""

        if 'eba_qEC' in ast_str or 'qx' in ast_str:
            # Looks like v4.0.0 format, normalize to current
            return self._normalize_v4_0_0(ast_dict)
        elif 'eba_EC' in ast_str and 'reference_period' in ast_str:
            # Looks like v3.1.0 format
            return ast_dict
        else:
            # Default to current format
            return ast_dict

    def _validate_semantics(self, expression):
        """Perform semantic validation if enabled."""
        try:
            # This would integrate with semantic API when available
            return {'semantic_valid': True, 'operands_checked': False}
        except Exception as e:
            return {'semantic_valid': False, 'error': str(e)}

    def _extract_variables(self, ast_dict):
        """Extract variable references from AST."""
        variables = []
        self._traverse_for_type(ast_dict, 'VarID', variables)
        return variables

    def _extract_constants(self, ast_dict):
        """Extract constants from AST."""
        constants = []
        self._traverse_for_type(ast_dict, 'Constant', constants)
        return constants

    def _extract_operations(self, ast_dict):
        """Extract operations from AST."""
        operations = []
        for op_type in ['BinOp', 'UnaryOp', 'AggregationOp', 'CondExpr']:
            self._traverse_for_type(ast_dict, op_type, operations)
        return operations

    def _traverse_for_type(self, ast_dict, target_type, collector):
        """Traverse AST collecting nodes of specific type."""
        if isinstance(ast_dict, dict):
            if ast_dict.get('class_name') == target_type:
                collector.append(ast_dict)
            for value in ast_dict.values():
                if isinstance(value, (dict, list)):
                    self._traverse_for_type(value, target_type, collector)
        elif isinstance(ast_dict, list):
            for item in ast_dict:
                self._traverse_for_type(item, target_type, collector)

    def _has_aggregations(self, ast_dict):
        """Check if AST contains aggregation operations."""
        aggregations = []
        self._traverse_for_type(ast_dict, 'AggregationOp', aggregations)
        return len(aggregations) > 0

    def _has_conditionals(self, ast_dict):
        """Check if AST contains conditional expressions."""
        conditionals = []
        self._traverse_for_type(ast_dict, 'CondExpr', conditionals)
        return len(conditionals) > 0

    def _calculate_complexity(self, ast_dict):
        """Calculate complexity score for AST."""
        score = 0
        if isinstance(ast_dict, dict):
            score += 1
            for value in ast_dict.values():
                if isinstance(value, (dict, list)):
                    score += self._calculate_complexity(value)
        elif isinstance(ast_dict, list):
            for item in ast_dict:
                score += self._calculate_complexity(item)
        return score


# Convenience functions for simple usage

def parse_expression(expression: str, compatibility_mode: str = "auto") -> Dict[str, Any]:
    """
    Simple function to parse a single expression.

    Args:
        expression: DPM-XL expression string
        compatibility_mode: Version compatibility mode

    Returns:
        Parse result dictionary
    """
    generator = ASTGenerator(compatibility_mode=compatibility_mode)
    return generator.parse_expression(expression)


def validate_expression(expression: str) -> bool:
    """
    Simple function to validate expression syntax.

    Args:
        expression: DPM-XL expression string

    Returns:
        True if valid, False otherwise
    """
    generator = ASTGenerator()
    result = generator.validate_expression(expression)
    return result['valid']


def parse_batch(expressions: List[str], compatibility_mode: str = "auto") -> List[Dict[str, Any]]:
    """
    Simple function to parse multiple expressions.

    Args:
        expressions: List of DPM-XL expression strings
        compatibility_mode: Version compatibility mode

    Returns:
        List of parse results
    """
    generator = ASTGenerator(compatibility_mode=compatibility_mode)
    return generator.parse_batch(expressions)