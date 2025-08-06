from antlr4 import InputStream, CommonTokenStream
from py_dpm.grammar.dist.suba.SubaLexer import SubaLexer
from py_dpm.grammar.dist.suba.SubaParser import SubaParser
from py_dpm.AST.SubaASTConstructor import SubaASTVisitor


def parse_suba_expression(expression_text: str):
    """
    Parse a SUBA expression and return an AST compatible with dpm_xl.
    
    Args:
        expression_text (str): The SUBA expression to parse
        
    Returns:
        AST: The root AST node (Start) containing the parsed expression
        
    Raises:
        Exception: If parsing fails
    """
    try:
        # Create input stream
        input_stream = InputStream(expression_text)
        
        # Create lexer
        lexer = SubaLexer(input_stream)
        
        # Create token stream
        token_stream = CommonTokenStream(lexer)
        
        # Create parser
        parser = SubaParser(token_stream)
        
        # Parse the formula (entry point)
        parse_tree = parser.formula()
        
        # Create AST visitor and visit the parse tree
        visitor = SubaASTVisitor()
        ast = visitor.visit(parse_tree)
        
        return ast
        
    except Exception as e:
        raise Exception(f"Failed to parse SUBA expression '{expression_text}': {str(e)}")


def validate_suba_syntax(expression_text: str) -> bool:
    """
    Validate SUBA expression syntax without generating AST.
    
    Args:
        expression_text (str): The SUBA expression to validate
        
    Returns:
        bool: True if syntax is valid, False otherwise
    """
    try:
        # Create input stream
        input_stream = InputStream(expression_text)
        
        # Create lexer
        lexer = SubaLexer(input_stream)
        
        # Create token stream
        token_stream = CommonTokenStream(lexer)
        
        # Create parser
        parser = SubaParser(token_stream)
        
        # Disable error output for validation
        parser.removeErrorListeners()
        
        # Parse the formula
        parse_tree = parser.formula()
        
        # Check if there were any syntax errors
        return parser.getNumberOfSyntaxErrors() == 0
        
    except Exception:
        return False


def get_suba_parse_tree(expression_text: str):
    """
    Get the raw ANTLR parse tree for a SUBA expression.
    Useful for debugging and understanding the parsing structure.
    
    Args:
        expression_text (str): The SUBA expression to parse
        
    Returns:
        ParseTree: The ANTLR parse tree
    """
    # Create input stream
    input_stream = InputStream(expression_text)
    
    # Create lexer
    lexer = SubaLexer(input_stream)
    
    # Create token stream
    token_stream = CommonTokenStream(lexer)
    
    # Create parser
    parser = SubaParser(token_stream)
    
    # Parse and return the tree
    return parser.formula()