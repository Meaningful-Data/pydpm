import re
from antlr4.tree.Tree import TerminalNodeImpl

from py_dpm.AST.ASTObjects import *
from py_dpm.Exceptions import exceptions
from py_dpm.Exceptions.exceptions import SemanticError
from py_dpm.grammar.dist.suba.SubaParser import SubaParser
from py_dpm.grammar.dist.suba.SubaParserVisitor import SubaParserVisitor


class SubaASTVisitor(SubaParserVisitor):
    """
    Class to walk the SUBA parse tree and generate an AST which nodes are defined at AST.ASTObjects
    """

    def visitFormula(self, ctx: SubaParser.FormulaContext):
        """Entry point for SUBA formula - maps to Start node"""
        expression = self.visit(ctx.expression(0))
        
        # Handle comparison at top level if present
        if ctx.getChildCount() > 1 and ctx.comparisonOp():
            left = expression
            op = self.visitComparisonOp(ctx.comparisonOp())
            right = self.visit(ctx.expression(1))
            expression = BinOp(left=left, op=op, right=right)
        
        # Create a Start node with the main expression
        return Start(children=[expression])

    def visitComparisonOp(self, ctx: SubaParser.ComparisonOpContext):
        """Map SUBA comparison operators to dpm_xl equivalents"""
        return ctx.getChild(0).symbol.text

    # Binary Operations
    def visitMultiplicativeExpr(self, ctx: SubaParser.MultiplicativeExprContext):
        return self._create_bin_op(ctx)

    def visitAdditiveExpr(self, ctx: SubaParser.AdditiveExprContext):
        return self._create_bin_op(ctx)

    def visitPowerExpr(self, ctx: SubaParser.PowerExprContext):
        return self._create_bin_op(ctx)

    def visitConcatExpr(self, ctx: SubaParser.ConcatExprContext):
        return self._create_bin_op(ctx)

    def visitComparisonExpr(self, ctx: SubaParser.ComparisonExprContext):
        return self._create_bin_op(ctx)

    def visitLogicalExpr(self, ctx: SubaParser.LogicalExprContext):
        return self._create_bin_op(ctx)

    def visitInExpr(self, ctx: SubaParser.InExprContext):
        left = self.visit(ctx.expression())
        right = self.visit(ctx.setExpression())
        return BinOp(left=left, op='in', right=right)

    def _create_bin_op(self, ctx):
        """Helper to create binary operations"""
        left = self.visit(ctx.expression(0))
        
        # Handle different operator types
        if hasattr(ctx, 'op') and ctx.op:
            op = ctx.op.text
        else:
            # Get the operator from the second child
            op_child = ctx.getChild(1)
            if hasattr(op_child, 'symbol'):
                op = op_child.symbol.text
            elif hasattr(op_child, 'getText'):
                op = op_child.getText()
            else:
                # It might be a ComparisonOpContext or similar
                op = self.visit(op_child)
        
        right = self.visit(ctx.expression(1))
        return BinOp(left=left, op=op, right=right)

    # Unary Operations
    def visitUnaryExpr(self, ctx: SubaParser.UnaryExprContext):
        op = ctx.op.text
        operand = self.visit(ctx.expression())
        return UnaryOp(op=op, operand=operand)

    def visitNotExpr(self, ctx: SubaParser.NotExprContext):
        op = 'not'
        operand = self.visit(ctx.expression())
        return UnaryOp(op=op, operand=operand)

    # Parenthesized expressions
    def visitParenthesizedExpr(self, ctx: SubaParser.ParenthesizedExprContext):
        expression = self.visit(ctx.expression())
        return ParExpr(expression=expression)

    # Conditional expressions
    def visitConditionalExpr(self, ctx: SubaParser.ConditionalExprContext):
        condition = self.visit(ctx.expression(0))
        then_expr = self.visit(ctx.expression(1))
        else_expr = self.visit(ctx.expression(2)) if ctx.getChildCount() > 6 else None
        return CondExpr(condition=condition, then_expr=then_expr, else_expr=else_expr)

    # Function calls
    def visitFunctionExpr(self, ctx: SubaParser.FunctionExprContext):
        return self.visit(ctx.functionCall())

    def visitFunctionCall(self, ctx: SubaParser.FunctionCallContext):
        child = ctx.getChild(0)
        return self.visit(child)

    # Aggregate functions
    def visitAggregateFunction(self, ctx: SubaParser.AggregateFunctionContext):
        op = ctx.getChild(0).symbol.text.lower()  # Convert to lowercase for compatibility
        operand = self.visit(ctx.expression())
        grouping_clause = None
        
        if ctx.groupByClause():
            grouping_clause = self.visit(ctx.groupByClause())
        
        return AggregationOp(op=op, operand=operand, grouping_clause=grouping_clause)

    def visitGroupByClause(self, ctx: SubaParser.GroupByClauseContext):
        components = []
        for i in range(1, ctx.getChildCount(), 2):  # Skip GROUP_BY and commas
            if ctx.getChild(i).symbol:
                components.append(ctx.getChild(i).symbol.text)
        return GroupingClause(components=components)

    # Math functions
    def visitUnaryMathFunction(self, ctx: SubaParser.UnaryMathFunctionContext):
        op = ctx.getChild(0).symbol.text.lower()
        operand = self.visit(ctx.expression())
        return UnaryOp(op=op, operand=operand)

    def visitBinaryMathFunction(self, ctx: SubaParser.BinaryMathFunctionContext):
        op = ctx.getChild(0).symbol.text.lower()
        left = self.visit(ctx.expression(0))
        right = self.visit(ctx.expression(1))
        return BinOp(op=op, left=left, right=right)

    def visitVariableMathFunction(self, ctx: SubaParser.VariableMathFunctionContext):
        op = ctx.getChild(0).symbol.text.lower()
        operands = []
        for expr in ctx.expressionList().expression():
            operands.append(self.visit(expr))
        return ComplexNumericOp(op=op, operands=operands)

    # String functions
    def visitStringFunction(self, ctx: SubaParser.StringFunctionContext):
        op = ctx.getChild(0).symbol.text.lower()  # 'len'
        operand = self.visit(ctx.expression())
        return UnaryOp(op=op, operand=operand)

    # Null functions
    def visitIsNullFunction(self, ctx: SubaParser.IsNullFunctionContext):
        operand = self.visit(ctx.expression())
        return UnaryOp(op='isnull', operand=operand)

    def visitNvlFunction(self, ctx: SubaParser.NvlFunctionContext):
        left = self.visit(ctx.expression(0))
        right = self.visit(ctx.expression(1))
        return BinOp(op='nvl', left=left, right=right)

    # Filter functions
    def visitFilterFunction(self, ctx: SubaParser.FilterFunctionContext):
        selection = self.visit(ctx.expression(0))
        condition = self.visit(ctx.expression(1))
        return FilterOp(selection=selection, condition=condition)

    # Time functions
    def visitTimeShiftFunction(self, ctx: SubaParser.TimeShiftFunctionContext):
        operand = self.visit(ctx.expression())
        period_indicator = ctx.timePeriod().getChild(0).symbol.text
        shift_number = ctx.INTEGER_LITERAL().symbol.text
        component = None
        
        # Check if there's a component specified
        if ctx.getChildCount() > 8:  # More than minimal args
            for child in ctx.children:
                if hasattr(child, 'symbol') and child.symbol.type == SubaParser.CODE:
                    component = Dimension(dimension_code=child.symbol.text)
                    break
        
        return TimeShiftOp(operand=operand, component=component, 
                          period_indicator=period_indicator, shift_number=shift_number)
    
    def visitDatetimeFunction(self, ctx: SubaParser.DatetimeFunctionContext):
        """Handle DATETIME function - converts string to datetime constant"""
        date_string = ctx.STRING_LITERAL().symbol.text[1:-1]  # Remove quotes
        return Constant(type_='Date', value=date_string)
    
    # Logical functions
    def visitLogicalFunctionCall(self, ctx: SubaParser.LogicalFunctionCallContext):
        """Handle LOGICAL function calls"""
        operand = self.visit(ctx.expression())
        return UnaryOp(op='LOGICAL', operand=operand)

    # Data point references - map to VarID
    def visitDataPointExpr(self, ctx: SubaParser.DataPointExprContext):
        return self.visit(ctx.dataPointReference())

    def visitDataPointReference(self, ctx: SubaParser.DataPointReferenceContext):
        """Convert SUBA data point reference to dpm_xl VarID"""
        data_point_spec = self.visit(ctx.dataPointSpec())
        
        # Handle modifiers (time shifts, etc.)
        if ctx.modifiers():
            # For now, return the basic data point spec
            # TODO: Handle modifiers properly
            pass
        
        return data_point_spec

    def visitDataPointSpec(self, ctx: SubaParser.DataPointSpecContext):
        child = ctx.getChild(0)
        return self.visit(child)

    def visitTsrcNotation(self, ctx: SubaParser.TsrcNotationContext):
        """Convert TSRC notation to VarID"""
        table = None
        rows = None
        cols = None
        sheets = None
        
        for component in ctx.tsrcComponent():
            comp_result = self.visit(component)
            if comp_result['type'] == 'table':
                table = comp_result['value']
            elif comp_result['type'] == 'row':
                rows = comp_result['value']
            elif comp_result['type'] == 'col':
                cols = comp_result['value']
            elif comp_result['type'] == 'sheet':
                sheets = comp_result['value']
        
        return VarID(table=table, rows=rows, cols=cols, sheets=sheets, 
                    interval=None, default=None, is_table_group=False)

    def visitTableComponent(self, ctx: SubaParser.TableComponentContext):
        table_code = self.visit(ctx.tableCode())
        return {'type': 'table', 'value': table_code}

    def visitSheetComponent(self, ctx: SubaParser.SheetComponentContext):
        cell_spec = self.visit(ctx.cellSpecifier())
        return {'type': 'sheet', 'value': cell_spec}

    def visitRowComponent(self, ctx: SubaParser.RowComponentContext):
        cell_spec = self.visit(ctx.cellSpecifier())
        return {'type': 'row', 'value': cell_spec}

    def visitColumnComponent(self, ctx: SubaParser.ColumnComponentContext):
        cell_spec = self.visit(ctx.cellSpecifier())
        return {'type': 'col', 'value': cell_spec}

    def visitTableCode(self, ctx: SubaParser.TableCodeContext):
        return ctx.getChild(0).symbol.text

    def visitSingleCell(self, ctx: SubaParser.SingleCellContext):
        return [self.visit(ctx.cellCode())]
    
    def visitCellCode(self, ctx: SubaParser.CellCodeContext):
        """Handle cell codes that can be either CODE or INTEGER_LITERAL"""
        return ctx.getChild(0).symbol.text

    def visitRangeCell(self, ctx: SubaParser.RangeCellContext):
        start = self.visit(ctx.cellCode(0))
        end = self.visit(ctx.cellCode(1))
        return [f"{start}-{end}"]

    def visitAllCells(self, ctx: SubaParser.AllCellsContext):
        return ['*']

    def visitCellList(self, ctx: SubaParser.CellListContext):
        cells = []
        # Collect all cellCode children (skip commas)
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            # Check if this child is a cellCode context
            if hasattr(child, 'getRuleIndex') and 'cellCode' in type(child).__name__:
                cells.append(self.visit(child))
        return cells

    def visitVariableIdNotation(self, ctx: SubaParser.VariableIdNotationContext):
        """Convert Variable ID notation to appropriate AST node"""
        prefix = ctx.getChild(0).symbol.text  # XBRL or VAR
        
        # Build variable reference from components
        components = []
        for comp in ctx.variableIdComponent():
            components.append(self.visit(comp))
        
        # Create a variable reference - for now treat as simple variable
        variable_name = "_".join(components)
        return VarRef(variable=variable_name)

    def visitVariableIdComponent(self, ctx: SubaParser.VariableIdComponentContext):
        code = ctx.getChild(0).symbol.text
        # Handle optional parenthesized part
        if ctx.getChildCount() > 1:
            paren_code = ctx.getChild(2).symbol.text  # Inside parentheses
            return f"{code}({paren_code})"
        return code

    def visitIndicatorNotation(self, ctx: SubaParser.IndicatorNotationContext):
        """Simple indicator notation"""
        code = ctx.getChild(0).symbol.text
        return VarRef(variable=code)

    # SDW references
    def visitSdwExpr(self, ctx: SubaParser.SdwExprContext):
        return self.visit(ctx.sdwReference())

    def visitSdwReference(self, ctx: SubaParser.SdwReferenceContext):
        # SDW.CODE - create a special variable reference
        code = ctx.getChild(2).symbol.text
        return VarRef(variable=f"SDW.{code}")

    # Set expressions
    def visitSetExpression(self, ctx: SubaParser.SetExpressionContext):
        return self.visit(ctx.expressionList())

    def visitExpressionList(self, ctx: SubaParser.ExpressionListContext):
        elements = []
        for expr in ctx.expression():
            elements.append(self.visit(expr))
        return Set(children=elements)

    def visitListExpr(self, ctx: SubaParser.ListExprContext):
        """List expressions in brackets"""
        return self.visit(ctx.expressionList())

    # Literals
    def visitLiteralExpr(self, ctx: SubaParser.LiteralExprContext):
        return self.visit(ctx.literal())
    
    def visitCodeExpr(self, ctx: SubaParser.CodeExprContext):
        """Handle CODE tokens used as expressions (e.g., '1' tokenized as CODE)"""
        code_text = ctx.CODE().symbol.text
        # Try to parse as integer first
        try:
            int_value = int(code_text)
            return Constant(type_='Integer', value=int_value)
        except ValueError:
            # If not an integer, treat as string
            return Constant(type_='String', value=code_text)

    def visitLiteral(self, ctx: SubaParser.LiteralContext):
        """Convert SUBA literals to Constants"""
        token = ctx.getChild(0).symbol
        value = token.text
        token_type = token.type

        if token_type == SubaParser.BOOLEAN_LITERAL:
            return Constant(type_='Boolean', value=value == 'true')
        elif token_type == SubaParser.NULL_LITERAL:
            return Constant(type_='Null', value=None)
        elif token_type == SubaParser.INTEGER_LITERAL:
            return Constant(type_='Integer', value=int(value))
        elif token_type == SubaParser.DECIMAL_LITERAL:
            return Constant(type_='Number', value=float(value))
        elif token_type == SubaParser.PERCENT_LITERAL:
            numeric_value = float(value.replace('%', '')) / 100
            return Constant(type_='Number', value=numeric_value)
        elif token_type == SubaParser.STRING_LITERAL:
            # Remove quotes
            clean_value = value[1:-1]
            if clean_value == 'null':
                raise SemanticError("0-3")
            return Constant(type_='String', value=clean_value)
        else:
            raise NotImplementedError(f"Literal type {token_type} not implemented")

    # Attribute and entity functions (SUBA specific)
    def visitAttributeFunction(self, ctx: SubaParser.AttributeFunctionContext):
        """Handle ATTRIBUTE function - create a special dimension reference"""
        attr_type = ctx.STRING_LITERAL(0).symbol.text[1:-1]  # Remove quotes
        attr_value = ctx.STRING_LITERAL(1).symbol.text[1:-1]  # Remove quotes
        # For now, treat as a dimension reference
        return Dimension(dimension_code=f"ATTRIBUTE({attr_type},{attr_value})")

    def visitEntityByAttributeFunction(self, ctx: SubaParser.EntityByAttributeFunctionContext):
        """Handle ENTITY_BY_ATTRIBUTE function"""
        attr_type = ctx.STRING_LITERAL(0).symbol.text[1:-1]  # Remove quotes
        attr_value = ctx.STRING_LITERAL(1).symbol.text[1:-1]  # Remove quotes
        # For now, treat as a dimension reference
        return Dimension(dimension_code=f"ENTITY_BY_ATTRIBUTE({attr_type},{attr_value})")