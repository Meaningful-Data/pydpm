from py_dpm.AST.ASTObjects import *
from collections import defaultdict


class DpmXlCodeGenerator:
    """
    Converts AST nodes back to DPM-XL source code.
    Handles optimization like WITH clause extraction for common table references.
    """
    
    def __init__(self):
        self.table_refs = defaultdict(list)  # Track table references for WITH optimization
        
    def generate(self, ast_node):
        """
        Generate DPM-XL code from an AST node.
        
        Args:
            ast_node: The root AST node (typically Start)
            
        Returns:
            str: DPM-XL source code
        """
        self.table_refs.clear()
        return self._visit(ast_node)
    
    def _visit(self, node):
        """Visit an AST node and generate code"""
        method_name = f'_visit_{type(node).__name__}'
        method = getattr(self, method_name, self._generic_visit)
        return method(node)
    
    def _generic_visit(self, node):
        """Fallback for unhandled node types"""
        raise NotImplementedError(f"Code generation not implemented for {type(node).__name__}")
    
    def _visit_Start(self, node):
        """Generate code for Start node"""
        if not node.children:
            return ""
        
        # Generate code for all children
        expressions = []
        for child in node.children:
            expr_code = self._visit(child)
            expressions.append(expr_code)
        
        # For now, just join with semicolons
        # TODO: Optimize by detecting common table references and using WITH
        return "; ".join(expressions)
    
    def _visit_BinOp(self, node):
        """Generate code for binary operations"""
        left_code = self._visit(node.left)
        right_code = self._visit(node.right)
        
        # Handle special operators
        if node.op == '&':  # Concatenation
            return f"{left_code} & {right_code}"
        elif node.op in ['=', '!=', '<', '<=', '>', '>=', 'and', 'or', 'xor']:
            return f"{left_code} {node.op} {right_code}"
        elif node.op in ['AND', 'OR', 'XOR']:
            # Map SUBA boolean operators to DPM-XL equivalents
            op_mapping = {
                'AND': 'and',
                'OR': 'or', 
                'XOR': 'xor'
            }
            return f"{left_code} {op_mapping[node.op]} {right_code}"
        elif node.op == '^=':
            return f"{left_code} != {right_code}"
        elif node.op in ['+', '-', '*', '/']:
            return f"{left_code} {node.op} {right_code}"
        elif node.op in ['in', 'IN']:
            return f"{left_code} in {right_code}"
        else:
            return f"{left_code} {node.op} {right_code}"
    
    def _visit_UnaryOp(self, node):
        """Generate code for unary operations"""
        operand_code = self._visit(node.operand)
        
        if node.op in ['not', 'NOT']:
            return f"not ({operand_code})"
        elif node.op in ['+', '-']:
            return f"{node.op}{operand_code}"
        elif node.op.lower() == 'logical':
            # LOGICAL function doesn't exist in DPM-XL, just return the operand
            # This is because DPM-XL expressions are already logical where needed
            return operand_code
        elif node.op in ['abs', 'exp', 'ln', 'sqrt', 'len', 'isnull']:
            return f"{node.op}({operand_code})"
        else:
            return f"{node.op}({operand_code})"
    
    def _visit_VarID(self, node):
        """Generate code for VarID (cell references)"""
        parts = []
        
        # Add table reference
        if node.table:
            if node.is_table_group:
                parts.append(f"g{node.table}")
            else:
                parts.append(f"t{node.table}")
        
        # Add rows
        if node.rows:
            if isinstance(node.rows, list):
                if len(node.rows) == 1:
                    parts.append(f"r{node.rows[0]}")
                else:
                    parts.append(f"r({','.join(['r' + r for r in node.rows])})")
            else:
                parts.append(f"r{node.rows}")
        
        # Add columns
        if node.cols:
            if isinstance(node.cols, list):
                if len(node.cols) == 1:
                    parts.append(f"c{node.cols[0]}")
                else:
                    parts.append(f"c({','.join(['c' + c for c in node.cols])})")
            else:
                parts.append(f"c{node.cols}")
        
        # Add sheets
        if node.sheets:
            if isinstance(node.sheets, list):
                if len(node.sheets) == 1:
                    parts.append(f"s{node.sheets[0]}")
                else:
                    parts.append(f"s({','.join(['s' + s for s in node.sheets])})")
            else:
                parts.append(f"s{node.sheets}")
        
        # Add additional arguments
        args = []
        if node.interval is not None:
            args.append(f"interval: {'true' if node.interval else 'false'}")
        if node.default is not None:
            if hasattr(node.default, 'value'):
                args.append(f"default: {self._visit(node.default)}")
            else:
                args.append(f"default: {node.default}")

        if args:
            parts.extend(args)

        # Store table reference for potential WITH optimization
        if node.table:
            table_key = f"t{node.table}" if not node.is_table_group else f"g{node.table}"
            self.table_refs[table_key].append(node)

        return "{" + ", ".join(parts) + "}"
    
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
            # Check if it's a DATETIME function result or just a date literal
            if '-' in str(node.value) and len(str(node.value)) >= 8:  # Looks like a date string
                return f"#{node.value}#"
            else:
                return f"#{node.value}#"
        elif node.type == 'TimePeriod':
            return f"#{node.value}#"
        elif node.type == 'TimeInterval':
            return f"#{node.value}#"
        else:
            return str(node.value)
    
    def _visit_VarRef(self, node):
        """Generate code for variable references"""
        return "{" + f"v{node.variable}" + "}"
    
    def _visit_ParExpr(self, node):
        """Generate code for parenthesized expressions"""
        return f"({self._visit(node.expression)})"
    
    def _visit_CondExpr(self, node):
        """Generate code for conditional expressions"""
        condition_code = self._visit(node.condition)
        then_code = self._visit(node.then_expr)
        
        if node.else_expr:
            else_code = self._visit(node.else_expr)
            return f"if {condition_code} then {then_code} else {else_code} endif"
        else:
            return f"if {condition_code} then {then_code} endif"
    
    def _visit_AggregationOp(self, node):
        """Generate code for aggregation operations"""
        operand_code = self._visit(node.operand)
        
        if node.grouping_clause:
            grouping_code = self._visit(node.grouping_clause)
            return f"{node.op}({operand_code} {grouping_code})"
        else:
            return f"{node.op}({operand_code})"
    
    def _visit_GroupingClause(self, node):
        """Generate code for grouping clauses"""
        components = ", ".join(node.components)
        return f"group by {components}"
    
    def _visit_ComplexNumericOp(self, node):
        """Generate code for complex numeric operations (max, min with multiple operands)"""
        operand_codes = [self._visit(operand) for operand in node.operands]
        return f"{node.op}({', '.join(operand_codes)})"
    
    def _visit_FilterOp(self, node):
        """Generate code for filter operations"""
        selection_code = self._visit(node.selection)
        condition_code = self._visit(node.condition)
        return f"filter({selection_code}, {condition_code})"
    
    def _visit_TimeShiftOp(self, node):
        """Generate code for time shift operations"""
        operand_code = self._visit(node.operand)
        component_code = ""
        if node.component:
            component_code = f", {self._visit(node.component)}"
        
        return f"time_shift({operand_code}, {node.period_indicator}, {node.shift_number}{component_code})"
    
    def _visit_WhereClauseOp(self, node):
        """Generate code for WHERE clauses"""
        operand_code = self._visit(node.operand)
        condition_code = self._visit(node.condition)
        return f"{operand_code}[where {condition_code}]"

    def _visit_GetOp(self, node):
        """Generate code for GET operations"""
        operand_code = self._visit(node.operand)
        component_code = self._visit(node.component)
        return f"{operand_code}[get {component_code}]"

    def _visit_RenameOp(self, node):
        """Generate code for RENAME operations"""
        operand_code = self._visit(node.operand)
        rename_codes = [self._visit(rename_node) for rename_node in node.rename_nodes]
        return f"{operand_code}[rename {', '.join(rename_codes)}]"

    def _visit_RenameNode(self, node):
        """Generate code for individual rename nodes"""
        old_name_code = self._visit(node.old_name)
        new_name_code = self._visit(node.new_name)
        return f"{old_name_code} to {new_name_code}"

    def _visit_Dimension(self, node):
        """Generate code for dimension references"""
        return node.dimension_code

    def _visit_Set(self, node):
        """Generate code for set literals"""
        element_codes = [self._visit(child) for child in node.children]
        return "{" + ", ".join(element_codes) + "}"
    
    def _visit_Scalar(self, node):
        """Generate code for scalar (item) references"""
        return f"[{node.item}]"
    
    def _visit_PropertyReference(self, node):
        """Generate code for property references"""
        return f"[{node.code}]"
    
    def _visit_OperationRef(self, node):
        """Generate code for operation references"""
        return "{" + f"o{node.operation_code}" + "}"
    
    def _visit_PreconditionItem(self, node):
        """Generate code for precondition items"""
        return "{" + f"v_{node.variable_id}" + "}"
    
    def _visit_WithExpression(self, node):
        """Generate code for WITH expressions"""
        partial_code = self._visit(node.partial_selection)
        expression_code = self._visit(node.expression)
        return f"with {partial_code}: {expression_code}"
    
    def _visit_PersistentAssignment(self, node):
        """Generate code for persistent assignments"""
        left_code = self._visit(node.left)
        right_code = self._visit(node.right)
        return f"{left_code} <- {right_code}"
    
    def _visit_TemporaryAssignment(self, node):
        """Generate code for temporary assignments"""
        left_code = self._visit(node.left)
        right_code = self._visit(node.right)
        return f"{left_code} := {right_code}"
    
    def _visit_TemporaryIdentifier(self, node):
        """Generate code for temporary identifiers"""
        return node.value


class OptimizedDpmXlCodeGenerator(DpmXlCodeGenerator):
    """
    Extended code generator that optimizes output by extracting common patterns
    like WITH clauses for repeated table references.
    """
    
    def generate(self, ast_node):
        """
        Generate optimized DPM-XL code from an AST node.

        Args:
            ast_node: The root AST node (typically Start)

        Returns:
            str: Optimized DPM-XL source code
        """
        self.table_refs.clear()
        code = self._visit(ast_node)

        # Try to optimize with WITH clauses
        return self._optimize_with_clauses(ast_node, code)
    
    def _optimize_with_clauses(self, ast_node, original_code):
        """
        Analyze the AST to find common table references and optimize with WITH clauses.
        """
        # For now, implement a simple optimization for the most common case
        if not isinstance(ast_node, Start) or not ast_node.children:
            return original_code

        # Check if we have a single binary operation that could benefit from WITH
        if len(ast_node.children) == 1 and isinstance(ast_node.children[0], BinOp):
            return self._optimize_binary_expression(ast_node.children[0])

        return original_code
    
    def _optimize_binary_expression(self, bin_op):
        """
        Optimize a binary expression by extracting common table references.
        """
        # Find all VarID nodes in the expression
        var_ids = self._find_var_ids(bin_op)

        if not var_ids:
            return self._visit(bin_op)

        # Group by table and find common components
        table_groups = defaultdict(list)
        for var_id in var_ids:
            if var_id.table:
                table_key = f"t{var_id.table}" if not var_id.is_table_group else f"g{var_id.table}"
                table_groups[table_key].append(var_id)

        # Check if we can extract a WITH clause
        for table_key, var_id_list in table_groups.items():
            if len(var_id_list) >= 2:  # At least 2 references to same table
                # Find common columns
                common_cols = self._find_common_columns(var_id_list)

                if common_cols:
                    # Generate optimized WITH expression
                    return self._generate_with_expression(bin_op, table_key, common_cols, var_id_list)

        # No optimization possible
        return self._visit(bin_op)
    
    def _find_var_ids(self, node):
        """Recursively find all VarID nodes in an expression"""
        var_ids = []

        if isinstance(node, VarID):
            var_ids.append(node)
        elif hasattr(node, 'left') and hasattr(node, 'right'):
            var_ids.extend(self._find_var_ids(node.left))
            var_ids.extend(self._find_var_ids(node.right))
        elif hasattr(node, 'operand'):
            var_ids.extend(self._find_var_ids(node.operand))
        elif hasattr(node, 'expression'):
            var_ids.extend(self._find_var_ids(node.expression))

        return var_ids

    def _find_common_columns(self, var_id_list):
        """Find common column specifications across VarID nodes"""
        if not var_id_list:
            return None

        # For simplicity, check if all have the same columns
        first_cols = var_id_list[0].cols
        if all(var_id.cols == first_cols for var_id in var_id_list):
            return first_cols

        return None

    def _generate_with_expression(self, expression, table_key, common_cols, var_id_list):
        """Generate a WITH expression for common table/column references"""
        # Create partial selection
        partial_parts = [table_key]

        if common_cols:
            if isinstance(common_cols, list):
                if len(common_cols) == 1:
                    partial_parts.append(f"c{common_cols[0]}")
                else:
                    partial_parts.append(f"c({','.join(common_cols)})")
            else:
                partial_parts.append(f"c{common_cols}")

        # Check for common default/interval settings
        first_var = var_id_list[0]
        if first_var.default is not None:
            if hasattr(first_var.default, 'value'):
                partial_parts.append(f"default: {self._visit(first_var.default)}")
            else:
                partial_parts.append(f"default: {first_var.default}")

        if first_var.interval is not None:
            partial_parts.append(f"interval: {'true' if first_var.interval else 'false'}")

        partial_selection = "{" + ", ".join(partial_parts) + "}"

        # Generate simplified expression by removing common parts from VarIDs
        simplified_expression = self._simplify_expression_for_with(expression, table_key, common_cols)

        return f"with {partial_selection}: {simplified_expression}"

    def _simplify_expression_for_with(self, expression, table_key, common_cols):
        """Simplify expression by removing table and common column references"""
        # Create a simplified version by generating VarIDs without table/column info
        return self._visit_simplified(expression, table_key, common_cols)

    def _visit_simplified(self, node, table_key, common_cols):
        """Visit node with simplified VarID generation for WITH expressions"""
        if isinstance(node, VarID) and node.table:
            current_table_key = f"t{node.table}" if not node.is_table_group else f"g{node.table}"
            if current_table_key == table_key and node.cols == common_cols:
                # Generate simplified reference with just rows
                if node.rows:
                    if isinstance(node.rows, list):
                        if len(node.rows) == 1:
                            return "{" + f"r{node.rows[0]}" + "}"
                        else:
                            return "{" + f"r({','.join(node.rows)})" + "}"
                    else:
                        return "{" + f"r{node.rows}" + "}"
                else:
                    return "{}"
        elif isinstance(node, BinOp):
            # Handle binary operations recursively
            left_code = self._visit_simplified(node.left, table_key, common_cols)
            right_code = self._visit_simplified(node.right, table_key, common_cols)

            if node.op == '&':  # Concatenation
                return f"{left_code} & {right_code}"
            elif node.op in ['=', '!=', '<', '<=', '>', '>=', 'and', 'or', 'xor']:
                return f"{left_code} {node.op} {right_code}"
            elif node.op in ['+', '-', '*', '/']:
                return f"{left_code} {node.op} {right_code}"
            elif node.op == 'in':
                return f"{left_code} in {right_code}"
            else:
                return f"{left_code} {node.op} {right_code}"
        elif isinstance(node, UnaryOp):
            # Handle unary operations
            operand_code = self._visit_simplified(node.operand, table_key, common_cols)
            if node.op == 'not':
                return f"not ({operand_code})"
            elif node.op in ['+', '-']:
                return f"{node.op}{operand_code}"
            elif node.op in ['abs', 'exp', 'ln', 'sqrt', 'len', 'isnull']:
                return f"{node.op}({operand_code})"
            else:
                return f"{node.op}({operand_code})"

        # For other nodes, use normal generation
        return self._visit(node)