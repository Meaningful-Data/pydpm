"""
DpmXlParsingUtils.py
===================

Description
-----------
Utility functions for parsing DPM-XL expressions to AST.
"""

from antlr4 import InputStream, CommonTokenStream
from py_dpm.grammar.dist.dpm_xlLexer import dpm_xlLexer
from py_dpm.grammar.dist.dpm_xlParser import dpm_xlParser
from py_dpm.AST.ASTConstructor import ASTVisitor


def parse_dpm_xl_expression(expression_text: str):
    """
    Parse a DPM-XL expression and return an AST.
    
    Args:
        expression_text (str): The DPM-XL expression to parse
        
    Returns:
        AST: The root AST node (Start) containing the parsed expression
        
    Raises:
        Exception: If parsing fails
    """
    try:
        # Create input stream
        input_stream = InputStream(expression_text)
        
        # Create lexer
        lexer = dpm_xlLexer(input_stream)
        
        # Create token stream
        token_stream = CommonTokenStream(lexer)
        
        # Create parser
        parser = dpm_xlParser(token_stream)
        
        # Parse the start rule (entry point)
        parse_tree = parser.start()
        
        # Create AST visitor and visit the parse tree
        visitor = ASTVisitor()
        ast = visitor.visit(parse_tree)
        
        return ast
        
    except Exception as e:
        raise Exception(f"Failed to parse DPM-XL expression '{expression_text}': {str(e)}")


def validate_dpm_xl_syntax(expression_text: str) -> bool:
    """
    Validate DPM-XL expression syntax without generating AST.
    
    Args:
        expression_text (str): The DPM-XL expression to validate
        
    Returns:
        bool: True if syntax is valid, False otherwise
    """
    try:
        # Create input stream
        input_stream = InputStream(expression_text)
        
        # Create lexer
        lexer = dpm_xlLexer(input_stream)
        
        # Create token stream
        token_stream = CommonTokenStream(lexer)
        
        # Create parser
        parser = dpm_xlParser(token_stream)
        
        # Disable error output for validation
        parser.removeErrorListeners()
        
        # Parse the start rule
        parse_tree = parser.start()
        
        # Check if there were any syntax errors
        return parser.getNumberOfSyntaxErrors() == 0
        
    except Exception:
        return False


def get_dpm_xl_parse_tree(expression_text: str):
    """
    Get the raw ANTLR parse tree for a DPM-XL expression.
    Useful for debugging and understanding the parsing structure.
    
    Args:
        expression_text (str): The DPM-XL expression to parse
        
    Returns:
        ParseTree: The ANTLR parse tree
    """
    # Create input stream
    input_stream = InputStream(expression_text)
    
    # Create lexer
    lexer = dpm_xlLexer(input_stream)
    
    # Create token stream
    token_stream = CommonTokenStream(lexer)
    
    # Create parser
    parser = dpm_xlParser(token_stream)
    
    # Parse and return the tree
    return parser.start()