from py_dpm.AST.ASTObjects import *


class SubaCodeGenerator:
    """
    Converts AST nodes back to SUBA source code.
    Handles expansion of DPM-XL constructs like WITH clauses.
    """
    
    def __init__(self):
        self.with_context = None  # Track current WITH clause context
        
    def generate(self, ast_node):
        """
        Generate SUBA code from an AST node.
        
        Args:
            ast_node: The root AST node (typically Start)
            
        Returns:
            str: SUBA source code
        """
        self.with_context = None
        return self._visit(ast_node)
    
    def _visit(self, node):
        """Visit an AST node and generate code"""
        if node is None:
            return ""

        method_name = f'_visit_{type(node).__name__}'
        method = getattr(self, method_name, self._generic_visit)
        return method(node)
    
    def _generic_visit(self, node):
        """Fallback for unhandled node types"""
        raise NotImplementedError(f"SUBA code generation not implemented for {type(node).__name__}")
    
    def _visit_Start(self, node):
        """Generate code for Start node"""
        if not node.children:
            return ""
        
        # Generate code for all children
        expressions = []
        for child in node.children:
            expr_code = self._visit(child)
            expressions.append(expr_code)
        
        return " ".join(expressions)
    
    def _visit_BinOp(self, node):
        """Generate code for binary operations"""
        left_code = self._visit(node.left)
        right_code = self._visit(node.right)
        
        # Define boolean operations that need LOGICAL wrapping in SUBA
        boolean_ops = ['=', '!=', '^=', '<', '<=', '>', '>=', 'and', 'or', 'xor', 'AND', 'OR', 'XOR', 'in', 'IN']
        
        # Handle different operators
        if node.op == '&':  # Concatenation
            return f"{left_code} & {right_code}"
        elif node.op in ['+', '-', '*', '/']:
            return f"{left_code} {node.op} {right_code}"
        elif node.op == '**':
            return f"{left_code} ** {right_code}"
        elif node.op in boolean_ops:
            # Map DPM-XL operators to SUBA equivalents
            op_mapping = {
                '!=': '^=',
                'and': 'AND',
                'or': 'OR',
                'xor': 'XOR',
                'in': 'IN'
            }
            suba_op = op_mapping.get(node.op, node.op)
            boolean_expr = f"{left_code} {suba_op} {right_code}"
            
            # Wrap boolean expressions in LOGICAL() function for SUBA
            return f"LOGICAL({boolean_expr})"
        else:
            # For other operators, use as-is
            return f"{left_code} {node.op} {right_code}"
    
    def _visit_UnaryOp(self, node):
        """Generate code for unary operations"""
        operand_code = self._visit(node.operand)
        
        if node.op == 'not':
            # NOT is a boolean operation that should be wrapped in LOGICAL for SUBA
            return f"LOGICAL(NOT {operand_code})"
        elif node.op in ['+', '-']:
            return f"{node.op}{operand_code}"
        elif node.op.upper() == 'LOGICAL':
            return f"LOGICAL({operand_code})"
        elif node.op.upper() in ['ABS', 'EXP', 'LN', 'SQRT', 'LEN', 'ISNULL']:
            return f"{node.op.upper()}({operand_code})"
        else:
            return f"{node.op.upper()}({operand_code})"
    
    def _visit_VarID(self, node):
        """Generate code for VarID (cell references) - expand WITH context"""
        # Build full SUBA data point reference
        components = []
        
        # Table component
        table = node.table
        if self.with_context and self.with_context.get('table'):
            table = self.with_context['table']
        elif not table and self.with_context and self.with_context.get('table'):
            table = self.with_context['table']
        
        if table:
            components.append(f"T({table})")

        # Row component
        rows = node.rows
        if rows:
            if isinstance(rows, list):
                if len(rows) == 1:
                    components.append(f"R({rows[0]})")
                else:
                    components.append(f"R({','.join(rows)})")
            else:
                components.append(f"R({rows})")
        
        # Column component
        cols = node.cols
        if self.with_context and self.with_context.get('cols'):
            cols = self.with_context['cols']
        elif not cols and self.with_context and self.with_context.get('cols'):
            cols = self.with_context['cols']

        if cols:
            if isinstance(cols, list):
                if len(cols) == 1:
                    components.append(f"C({cols[0]})")
                else:
                    components.append(f"C({','.join(cols)})")
            else:
                components.append(f"C({cols})")
        
        # Sheet component
        sheets = node.sheets
        if self.with_context and self.with_context.get('sheets'):
            sheets = self.with_context['sheets']
        elif not sheets and self.with_context and self.with_context.get('sheets'):
            sheets = self.with_context['sheets']

        if sheets:
            if isinstance(sheets, list):
                if len(sheets) == 1:
                    components.append(f"S({sheets[0]})")
                else:
                    components.append(f"S({','.join(sheets)})")
            else:
                components.append(f"S({sheets})")
        
        return "{" + "".join(components) + "}"
    
    def _visit_Constant(self, node):
        """Generate code for constants"""
        if node.type == 'String':
            return f'"{node.value}"'
        elif node.type == 'Boolean':
            return 'true' if node.value else 'false'
        elif node.type == 'Null':
            return 'null'
        elif node.type in ['Integer', 'Number']:
            return str(node.value)
        elif node.type == 'Date':
            # Convert from DPM-XL #date# format to SUBA DATETIME('date') format
            return f"DATETIME('{node.value}')"
        elif node.type == 'TimePeriod':
            return f"'{node.value}'"
        elif node.type == 'TimeInterval':
            return f"'{node.value}'"
        else:
            return str(node.value)
    
    def _visit_VarRef(self, node):
        """Generate code for variable references"""
        return "{" + f"VAR:{node.variable}" + "}"
    
    def _visit_ParExpr(self, node):
        """Generate code for parenthesized expressions"""
        return f"({self._visit(node.expression)})"
    
    def _visit_CondExpr(self, node):
        """Generate code for conditional expressions"""
        condition_code = self._visit(node.condition)
        then_code = self._visit(node.then_expr)
        
        if node.else_expr:
            else_code = self._visit(node.else_expr)
            return f"IF {condition_code} THEN {then_code} ELSE {else_code} ENDIF"
        else:
            return f"IF {condition_code} THEN {then_code} ENDIF"
    
    def _visit_AggregationOp(self, node):
        """Generate code for aggregation operations"""
        operand_code = self._visit(node.operand)
        
        if node.grouping_clause:
            grouping_code = self._visit(node.grouping_clause)
            return f"{node.op.upper()}({operand_code}, {grouping_code})"
        else:
            return f"{node.op.upper()}({operand_code})"
    
    def _visit_GroupingClause(self, node):
        """Generate code for grouping clauses"""
        components = ", ".join(node.components)
        return f"GROUP_BY {components}"
    
    def _visit_ComplexNumericOp(self, node):
        """Generate code for complex numeric operations (max, min with multiple operands)"""
        operand_codes = [self._visit(operand) for operand in node.operands]
        return f"{node.op.upper()}({', '.join(operand_codes)})"
    
    def _visit_FilterOp(self, node):
        """Generate code for filter operations"""
        selection_code = self._visit(node.selection)
        condition_code = self._visit(node.condition)
        return f"FILTER({selection_code}, {condition_code})"
    
    def _visit_TimeShiftOp(self, node):
        """Generate code for time shift operations"""
        operand_code = self._visit(node.operand)
        component_code = ""
        if node.component:
            component_code = f", {self._visit(node.component)}"
        
        return f"TIME_SHIFT({operand_code}, {node.period_indicator}, {node.shift_number}{component_code})"
    
    def _visit_Set(self, node):
        """Generate code for set literals"""
        element_codes = [self._visit(child) for child in node.children]
        return "{" + ", ".join(element_codes) + "}"
    
    def _visit_Scalar(self, node):
        """Generate code for scalar (item) references"""
        return f"[{node.item}]"
    
    def _visit_PropertyReference(self, node):
        """Generate code for property references"""
        return node.code
    
    def _visit_OperationRef(self, node):
        """Generate code for operation references"""
        return "{" + f"o{node.operation_code}" + "}"
    
    def _visit_PreconditionItem(self, node):
        """Generate code for precondition items"""
        return "{" + f"v_{node.variable_id}" + "}"
    
    def _visit_WithExpression(self, node):
        """
        Generate code for WITH expressions by expanding them to full SUBA format.
        This is the key transformation from DPM-XL back to SUBA.
        """
        # Parse the partial selection to extract common components
        partial_context = self._parse_partial_selection(node.partial_selection)

        # Set context for expanding simplified references
        old_context = self.with_context
        self.with_context = partial_context

        try:
            # Generate the expression with expanded context
            expression_code = self._visit(node.expression)
            return expression_code
        finally:
            # Restore previous context
            self.with_context = old_context
    
    def _parse_partial_selection(self, partial_selection):
        """
        Parse a partial selection VarID to extract common components.
        Example: {tC_17.01.a, c0010-0080} -> {'table': 'C_17.01.a', 'cols': '0010-0080'}
        """
        context = {}

        if isinstance(partial_selection, VarID):
            if partial_selection.table:
                context['table'] = partial_selection.table
            if partial_selection.rows:
                context['rows'] = partial_selection.rows
            if partial_selection.cols:
                context['cols'] = partial_selection.cols
            if partial_selection.sheets:
                context['sheets'] = partial_selection.sheets

        return context

    def _visit_PersistentAssignment(self, node):
        """Generate code for persistent assignments - not typically in SUBA"""
        left_code = self._visit(node.left)
        right_code = self._visit(node.right)
        return f"{left_code} <- {right_code}"
    
    def _visit_TemporaryAssignment(self, node):
        """Generate code for temporary assignments - not typically in SUBA"""
        left_code = self._visit(node.left)
        right_code = self._visit(node.right)
        return f"{left_code} := {right_code}"
    
    def _visit_TemporaryIdentifier(self, node):
        """Generate code for temporary identifiers - not typically in SUBA"""
        return node.value
    
    def _visit_WhereClauseOp(self, node):
        """Generate code for WHERE clauses - not standard SUBA, but may need to handle"""
        operand_code = self._visit(node.operand)
        condition_code = self._visit(node.condition)
        return f"FILTER({operand_code}, {condition_code})"
    
    def _visit_GetOp(self, node):
        """Generate code for GET operations - not standard SUBA"""
        # GET operations don't have direct SUBA equivalents
        # For now, just return the operand
        return self._visit(node.operand)
    
    def _visit_RenameOp(self, node):
        """Generate code for RENAME operations - not standard SUBA"""
        # RENAME operations don't have direct SUBA equivalents
        # For now, just return the operand
        return self._visit(node.operand)
    
    def _visit_Dimension(self, node):
        """Generate code for dimension references"""
        return node.dimension_code