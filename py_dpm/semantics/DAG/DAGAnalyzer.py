import numpy as np
import networkx as nx

from py_dpm.AST.ASTObjects import Start, PersistentAssignment, WithExpression, AST, OperationRef, TemporaryAssignment
from py_dpm.AST.ASTTemplate import ASTTemplate
from py_dpm.Exceptions import exceptions
from py_dpm.Utils.tokens import INPUTS, OUTPUTS


class DAGAnalyzer(ASTTemplate):
    """
    Class to generate the Direct Acyclic Graph from calculations scripts.
    """

    def __init__(self):
        super().__init__()
        self.inputs: list = []
        self.outputs: list = []
        self.dependencies: dict = {}
        self.calculation_number = 1

        self.vertex: dict = {}
        self.edges: dict = {}
        self.number_of_vertex: int = 0
        self.adjacency_matrix = None
        self.sorting = None

        self.graph = None

    def create_DAG(self, ast: AST):
        """
        Method to generate the Direct  Acyclic Graph from ast
        """
        self.visit(ast)

        self.load_vertex()
        self.load_edges()
        self.create_adjacency_matrix()

        try:
            self.nx_topological_sort()
            if len(self.edges):
                self.sort_ast(ast=ast)

        except nx.NetworkXUnfeasible:
            graph_cycles = nx.find_cycle(self.graph)
            pos1, pos2 = graph_cycles[0]
            op1 = self.vertex[pos1]
            op2 = self.vertex[pos2]
            raise exceptions.ScriptingError(code="6-4", op1=op1, op2=op2)

    def load_vertex(self):
        """

        """

        for key, calculation in self.dependencies.items():
            outputs = calculation[OUTPUTS]
            if len(outputs) > 0:
                self.vertex[key] = outputs[0]
        self.number_of_vertex = len(self.vertex)

    def load_edges(self):
        """

        """
        if len(self.vertex) > 0:
            number_of_edges = 0
            for key, calculation in self.dependencies.items():
                outputs = calculation[OUTPUTS]
                if len(outputs) > 0:
                    output = outputs[0]
                    for sub_key, sub_calculation in self.dependencies.items():
                        inputs = sub_calculation[INPUTS]
                        if inputs and output in inputs:
                            self.edges[number_of_edges] = (key, sub_key)
                            number_of_edges += 1

    def create_adjacency_matrix(self):
        """

        """
        self.adjacency_matrix = np.zeros((self.number_of_vertex, self.number_of_vertex), dtype=int)
        for edge in list(self.edges.values()):
            self.adjacency_matrix[edge[0] - 1][edge[1] - 1] = 1

    def nx_topological_sort(self):
        """

        """
        edges = list(self.edges.values())
        self.graph = DAG = nx.DiGraph()
        DAG.add_nodes_from(self.vertex)
        DAG.add_edges_from(edges)
        self.sorting = list(nx.topological_sort(DAG))

    def sort_ast(self, ast):
        """

        """
        lst = []
        calculations = list(ast.children)
        for x in self.sorting:
            for i in range(len(calculations)):
                if i == x - 1:
                    lst.append(calculations[i])
        self.check_overwriting(lst)
        ast.children = lst

    def check_overwriting(self, outputs):
        """

        """
        non_repeated = []
        outputs_lst = []
        for output in outputs:
            if isinstance(output, TemporaryAssignment):
                temporary_identifier_value = output.left.value
                outputs_lst.append(temporary_identifier_value)
                if isinstance(output.right, PersistentAssignment):
                    outputs_lst.append(output.right.left.variable)
        for output_value in outputs_lst:
            if output_value not in non_repeated:
                non_repeated.append(output_value)
            else:
                raise exceptions.SemanticError("6-1", variable=output_value)

    def get_calculation_structure(self):
        """

        """
        inputs = list(set(self.inputs))
        outputs = list(set(self.outputs))

        return {INPUTS: inputs, OUTPUTS: outputs}

    def visit_Start(self, node: Start):
        for child in node.children:
            self.visit(child)
            self.dependencies[self.calculation_number] = self.get_calculation_structure()

            self.calculation_number += 1

            self.inputs = []
            self.outputs = []

    def visit_PersistentAssignment(self, node: PersistentAssignment):
        self.visit(node.right)

    def visit_TemporaryAssignment(self, node: TemporaryAssignment):
        self.outputs.append(node.left.value)
        self.visit(node.right)

    def visit_OperationRef(self, node: OperationRef):
        self.inputs.append(node.operation_code)

    def visit_WithExpression(self, node: WithExpression):
        self.visit(node.expression)
