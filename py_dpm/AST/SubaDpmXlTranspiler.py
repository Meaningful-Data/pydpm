from py_dpm.AST.SubaParsingUtils import parse_suba_expression, validate_suba_syntax
from py_dpm.AST.DpmXlParsingUtils import parse_dpm_xl_expression, validate_dpm_xl_syntax
from py_dpm.AST.DpmXlCodeGenerator import OptimizedDpmXlCodeGenerator, DpmXlCodeGenerator
from py_dpm.AST.SubaCodeGenerator import SubaCodeGenerator
from py_dpm.AST.ASTObjects import *


class SubaToDpmXlTranspiler:
    """
    Transpiler that converts SUBA expressions to DPM-XL expressions.
    
    The conversion process:
    1. Parse SUBA expression to AST
    2. Apply any necessary AST transformations
    3. Generate DPM-XL code from AST
    """
    
    def __init__(self, optimize=True):
        """
        Initialize the transpiler.
        
        Args:
            optimize (bool): Whether to use optimized code generation (WITH clauses, etc.)
        """
        self.optimize = optimize
        if optimize:
            self.code_generator = OptimizedDpmXlCodeGenerator()
        else:
            self.code_generator = DpmXlCodeGenerator()
    
    def transpile(self, suba_expression):
        """
        Convert a SUBA expression to DPM-XL.
        
        Args:
            suba_expression (str): The SUBA expression to convert
            
        Returns:
            str: The equivalent DPM-XL expression
            
        Raises:
            ValueError: If the SUBA expression is invalid
            Exception: If transpilation fails
        """
        try:
            # Step 1: Validate SUBA syntax
            if not validate_suba_syntax(suba_expression):
                raise ValueError(f"Invalid SUBA syntax: {suba_expression}")
            
            # Step 2: Parse SUBA to AST
            ast = parse_suba_expression(suba_expression)
            
            # Step 3: Apply any necessary transformations
            transformed_ast = self._transform_ast(ast)
            
            # Step 4: Generate DPM-XL code
            dpm_xl_code = self.code_generator.generate(transformed_ast)
            
            return dpm_xl_code
            
        except Exception as e:
            raise Exception(f"Failed to transpile SUBA expression '{suba_expression}': {str(e)}")
    
    def _transform_ast(self, ast):
        """
        Apply any necessary AST transformations for SUBA->DPM-XL conversion.
        
        Currently, the SUBA AST visitor already generates compatible AST nodes,
        so no major transformations are needed. This method is a placeholder
        for future enhancements.
        
        Args:
            ast: The AST from SUBA parsing
            
        Returns:
            The transformed AST
        """
        # For now, no transformations needed
        return ast
    
    def validate_suba(self, suba_expression):
        """
        Validate a SUBA expression without transpiling.
        
        Args:
            suba_expression (str): The SUBA expression to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        return validate_suba_syntax(suba_expression)
    
    def get_ast(self, suba_expression):
        """
        Get the AST for a SUBA expression without generating DPM-XL code.
        Useful for debugging and analysis.
        
        Args:
            suba_expression (str): The SUBA expression to parse
            
        Returns:
            AST: The parsed AST
        """
        return parse_suba_expression(suba_expression)


class DpmXlToSubaTranspiler:
    """
    Reverse transpiler that converts DPM-XL expressions to SUBA expressions.
    
    The conversion process:
    1. Parse DPM-XL expression to AST
    2. Apply AST transformations (expand WITH clauses, etc.)
    3. Generate SUBA code from transformed AST
    """
    
    def __init__(self):
        """Initialize the reverse transpiler."""
        self.suba_generator = SubaCodeGenerator()
    
    def transpile(self, dpm_xl_expression):
        """
        Convert a DPM-XL expression to SUBA.
        
        Args:
            dpm_xl_expression (str): The DPM-XL expression to convert
            
        Returns:
            str: The equivalent SUBA expression
            
        Raises:
            ValueError: If the DPM-XL expression is invalid
            Exception: If transpilation fails
        """
        try:
            # Step 1: Validate DPM-XL syntax
            if not validate_dpm_xl_syntax(dpm_xl_expression):
                raise ValueError(f"Invalid DPM-XL syntax: {dpm_xl_expression}")
            
            # Step 2: Parse DPM-XL to AST
            ast = parse_dpm_xl_expression(dpm_xl_expression)
            
            # Step 3: Apply any necessary transformations
            transformed_ast = self._transform_ast_for_suba(ast)
            
            # Step 4: Generate SUBA code
            suba_code = self.suba_generator.generate(transformed_ast)
            
            return suba_code
            
        except Exception as e:
            raise Exception(f"Failed to transpile DPM-XL expression '{dpm_xl_expression}': {str(e)}")
    
    def _transform_ast_for_suba(self, ast):
        """
        Apply necessary AST transformations for DPM-XL to SUBA conversion.
        
        Main transformations:
        - WITH clauses are handled by the SUBA code generator
        - DPM-XL specific operators are mapped to SUBA equivalents
        - Complex constructs are simplified where possible
        
        Args:
            ast: The AST from DPM-XL parsing
            
        Returns:
            The transformed AST ready for SUBA generation
        """
        # For now, most transformations are handled in the SUBA code generator
        # Future enhancements could include:
        # - Simplifying complex DPM-XL constructs
        # - Optimizing the AST structure for SUBA generation
        # - Handling edge cases in conversion
        
        return ast
    
    def validate_dpm_xl(self, dpm_xl_expression):
        """
        Validate a DPM-XL expression without transpiling.
        
        Args:
            dpm_xl_expression (str): The DPM-XL expression to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        return validate_dpm_xl_syntax(dpm_xl_expression)
    
    def get_ast(self, dpm_xl_expression):
        """
        Get the AST for a DPM-XL expression without generating SUBA code.
        Useful for debugging and analysis.
        
        Args:
            dpm_xl_expression (str): The DPM-XL expression to parse
            
        Returns:
            AST: The parsed AST
        """
        return parse_dpm_xl_expression(dpm_xl_expression)


class TranspilerUtils:
    """
    Utility functions for transpilation tasks.
    """
    
    @staticmethod
    def analyze_expression(expression, is_suba=True):
        """
        Analyze an expression and return information about its structure.
        
        Args:
            expression (str): The expression to analyze
            is_suba (bool): True if expression is SUBA, False if DPM-XL
            
        Returns:
            dict: Analysis results including AST info, complexity metrics, etc.
        """
        try:
            if is_suba:
                transpiler = SubaToDpmXlTranspiler()
                ast = transpiler.get_ast(expression)
            else:
                reverse_transpiler = DpmXlToSubaTranspiler()
                ast = reverse_transpiler.get_ast(expression)
            
            analysis = {
                'valid': True,
                'ast_type': type(ast).__name__,
                'complexity': TranspilerUtils._calculate_complexity(ast),
                'table_references': TranspilerUtils._extract_table_references(ast),
                'operations': TranspilerUtils._extract_operations(ast)
            }
            
            return analysis
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'ast_type': None,
                'complexity': 0,
                'table_references': [],
                'operations': []
            }
    
    @staticmethod
    def _calculate_complexity(ast):
        """Calculate a simple complexity score for an AST"""
        if not ast:
            return 0
        
        complexity = 1
        
        # Add complexity for child nodes
        if hasattr(ast, 'children') and ast.children:
            for child in ast.children:
                complexity += TranspilerUtils._calculate_complexity(child)
        
        # Add complexity for specific node types
        if hasattr(ast, 'left'):
            complexity += TranspilerUtils._calculate_complexity(ast.left)
        if hasattr(ast, 'right'):
            complexity += TranspilerUtils._calculate_complexity(ast.right)
        if hasattr(ast, 'operand'):
            complexity += TranspilerUtils._calculate_complexity(ast.operand)
        if hasattr(ast, 'expression'):
            complexity += TranspilerUtils._calculate_complexity(ast.expression)
        
        return complexity
    
    @staticmethod
    def _extract_table_references(ast):
        """Extract all table references from an AST"""
        tables = []
        
        if isinstance(ast, VarID) and ast.table:
            table_ref = f"{'g' if ast.is_table_group else 't'}{ast.table}"
            if table_ref not in tables:
                tables.append(table_ref)
        
        # Recursively check child nodes
        if hasattr(ast, 'children') and ast.children:
            for child in ast.children:
                tables.extend(TranspilerUtils._extract_table_references(child))
        
        if hasattr(ast, 'left'):
            tables.extend(TranspilerUtils._extract_table_references(ast.left))
        if hasattr(ast, 'right'):
            tables.extend(TranspilerUtils._extract_table_references(ast.right))
        if hasattr(ast, 'operand'):
            tables.extend(TranspilerUtils._extract_table_references(ast.operand))
        if hasattr(ast, 'expression'):
            tables.extend(TranspilerUtils._extract_table_references(ast.expression))
        
        return list(set(tables))  # Remove duplicates
    
    @staticmethod
    def _extract_operations(ast):
        """Extract all operations from an AST"""
        operations = []
        
        if isinstance(ast, (BinOp, UnaryOp, AggregationOp)):
            if ast.op not in operations:
                operations.append(ast.op)
        
        # Recursively check child nodes
        if hasattr(ast, 'children') and ast.children:
            for child in ast.children:
                operations.extend(TranspilerUtils._extract_operations(child))
        
        if hasattr(ast, 'left'):
            operations.extend(TranspilerUtils._extract_operations(ast.left))
        if hasattr(ast, 'right'):
            operations.extend(TranspilerUtils._extract_operations(ast.right))
        if hasattr(ast, 'operand'):
            operations.extend(TranspilerUtils._extract_operations(ast.operand))
        if hasattr(ast, 'expression'):
            operations.extend(TranspilerUtils._extract_operations(ast.expression))
        
        return list(set(operations))  # Remove duplicates