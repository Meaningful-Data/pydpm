from typing import Dict, Any, Optional
from dataclasses import dataclass

# Import directly to avoid circular imports
from antlr4 import CommonTokenStream, InputStream
from py_dpm.dpm_xl.grammar.generated.dpm_xlLexer import dpm_xlLexer
from py_dpm.dpm_xl.grammar.generated.dpm_xlParser import dpm_xlParser
from py_dpm.dpm_xl.grammar.generated.listeners import DPMErrorListener
from py_dpm.dpm_xl.ast.constructor import ASTVisitor


@dataclass
class SyntaxValidationResult:
    """
    Result of syntax validation.
    
    Attributes:
        is_valid (bool): Whether the syntax is valid
        error_message (Optional[str]): Error message if validation failed
        expression (str): The original expression that was validated
    """
    is_valid: bool
    error_message: Optional[str]
    expression: str


class SyntaxAPI:
    """
    API for DPM-XL syntax validation and analysis.
    
    This class provides methods to validate DPM-XL expression syntax.
    """
    
    def __init__(self):
        """Initialize the Syntax API."""
        self.error_listener = DPMErrorListener()
        self.visitor = ASTVisitor()
    
    def validate_expression(self, expression: str) -> SyntaxValidationResult:
        """
        Validate the syntax of a DPM-XL expression.
        
        Args:
            expression (str): The DPM-XL expression to validate
            
        Returns:
            SyntaxValidationResult: Result containing validation status and details
            
        Example:
            >>> from pydpm.api import SyntaxAPI
            >>> syntax = SyntaxAPI()
            >>> result = syntax.validate_expression("{tC_01.00, r0100, c0010}")
            >>> print(result.is_valid)
            True
        """
        try:
            # Use direct ANTLR validation
            input_stream = InputStream(expression)
            lexer = dpm_xlLexer(input_stream)
            lexer._listeners = [self.error_listener]
            token_stream = CommonTokenStream(lexer)
            
            parser = dpm_xlParser(token_stream)
            parser._listeners = [self.error_listener]
            parse_tree = parser.start()
            
            if parser._syntaxErrors == 0:
                return SyntaxValidationResult(
                    is_valid=True,
                    error_message=None,
                    expression=expression
                )
            else:
                return SyntaxValidationResult(
                    is_valid=False,
                    error_message="Syntax errors detected",
                    expression=expression
                )
        except SyntaxError as e:
            return SyntaxValidationResult(
                is_valid=False,
                error_message=str(e),
                expression=expression
            )
        except Exception as e:
            return SyntaxValidationResult(
                is_valid=False,
                error_message=f"Unexpected error: {str(e)}",
                expression=expression
            )
    
    def parse_expression(self, expression: str):
        """
        Parse a DPM-XL expression and return the AST.
        
        Args:
            expression (str): The DPM-XL expression to parse
            
        Returns:
            AST: The Abstract Syntax Tree for the expression
            
        Raises:
            Exception: If parsing fails
            
        Example:
            >>> from pydpm.api import SyntaxAPI
            >>> syntax = SyntaxAPI()
            >>> ast = syntax.parse_expression("{tC_01.00, r0100, c0010}")
        """
        # Parse directly using ANTLR and AST visitor
        try:
            input_stream = InputStream(expression)
            lexer = dpm_xlLexer(input_stream)
            token_stream = CommonTokenStream(lexer)
            parser = dpm_xlParser(token_stream)
            parse_tree = parser.start()
            
            # Create AST visitor and visit the parse tree
            ast = self.visitor.visit(parse_tree)
            return ast
        except Exception as e:
            raise Exception(f"Failed to parse DPM-XL expression '{expression}': {str(e)}")
    
    def is_valid_syntax(self, expression: str) -> bool:
        """
            Quick check if expression has valid syntax.
        
        Args:
            expression (str): The DPM-XL expression to check
            
        Returns:
            bool: True if syntax is valid, False otherwise
            
        Example:
            >>> from pydpm.api import SyntaxAPI
            >>> syntax = SyntaxAPI()
            >>> is_valid = syntax.is_valid_syntax("{tC_01.00, r0100, c0010}")
        """
        # Use existing validate_expression method
        result = self.validate_expression(expression)
        return result.is_valid
    
    def __del__(self):
        """Clean up resources."""
        pass


# Convenience functions for direct usage
def validate_expression(expression: str) -> SyntaxValidationResult:
    """
    Convenience function to validate DPM-XL expression syntax.
    
    Args:
        expression (str): The DPM-XL expression to validate
        
    Returns:
        SyntaxValidationResult: Result containing validation status and details
        
    Example:
        >>> from pydpm.api.syntax import validate_expression
        >>> result = validate_expression("{tC_01.00, r0100, c0010}")
    """
    api = SyntaxAPI()
    return api.validate_expression(expression)


def is_valid_syntax(expression: str) -> bool:
    """
    Convenience function to check if expression has valid syntax.
    
    Args:
        expression (str): The DPM-XL expression to check
        
    Returns:
        bool: True if syntax is valid, False otherwise
        
    Example:
        >>> from pydpm.api.syntax import is_valid_syntax
        >>> is_valid = is_valid_syntax("{tC_01.00, r0100, c0010}")
    """
    api = SyntaxAPI()
    return api.is_valid_syntax(expression)

