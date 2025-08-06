# Generated from SubaParser.g4 by ANTLR 4.7.2
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .SubaParser import SubaParser
else:
    from SubaParser import SubaParser

# This class defines a complete generic visitor for a parse tree produced by SubaParser.

class SubaParserVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by SubaParser#formula.
    def visitFormula(self, ctx:SubaParser.FormulaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#powerExpr.
    def visitPowerExpr(self, ctx:SubaParser.PowerExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#dataPointExpr.
    def visitDataPointExpr(self, ctx:SubaParser.DataPointExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#sdwExpr.
    def visitSdwExpr(self, ctx:SubaParser.SdwExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#inExpr.
    def visitInExpr(self, ctx:SubaParser.InExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#logicalExpr.
    def visitLogicalExpr(self, ctx:SubaParser.LogicalExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#comparisonExpr.
    def visitComparisonExpr(self, ctx:SubaParser.ComparisonExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#additiveExpr.
    def visitAdditiveExpr(self, ctx:SubaParser.AdditiveExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#functionExpr.
    def visitFunctionExpr(self, ctx:SubaParser.FunctionExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#concatExpr.
    def visitConcatExpr(self, ctx:SubaParser.ConcatExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#notExpr.
    def visitNotExpr(self, ctx:SubaParser.NotExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#unaryExpr.
    def visitUnaryExpr(self, ctx:SubaParser.UnaryExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#parenthesizedExpr.
    def visitParenthesizedExpr(self, ctx:SubaParser.ParenthesizedExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#literalExpr.
    def visitLiteralExpr(self, ctx:SubaParser.LiteralExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#listExpr.
    def visitListExpr(self, ctx:SubaParser.ListExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#multiplicativeExpr.
    def visitMultiplicativeExpr(self, ctx:SubaParser.MultiplicativeExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#conditionalExpr.
    def visitConditionalExpr(self, ctx:SubaParser.ConditionalExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#comparisonOp.
    def visitComparisonOp(self, ctx:SubaParser.ComparisonOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#dataPointReference.
    def visitDataPointReference(self, ctx:SubaParser.DataPointReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#dataArea.
    def visitDataArea(self, ctx:SubaParser.DataAreaContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#dataPointSpec.
    def visitDataPointSpec(self, ctx:SubaParser.DataPointSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#tsrcNotation.
    def visitTsrcNotation(self, ctx:SubaParser.TsrcNotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#tableComponent.
    def visitTableComponent(self, ctx:SubaParser.TableComponentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#sheetComponent.
    def visitSheetComponent(self, ctx:SubaParser.SheetComponentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#rowComponent.
    def visitRowComponent(self, ctx:SubaParser.RowComponentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#columnComponent.
    def visitColumnComponent(self, ctx:SubaParser.ColumnComponentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#tableCode.
    def visitTableCode(self, ctx:SubaParser.TableCodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#singleCell.
    def visitSingleCell(self, ctx:SubaParser.SingleCellContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#rangeCell.
    def visitRangeCell(self, ctx:SubaParser.RangeCellContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#allCells.
    def visitAllCells(self, ctx:SubaParser.AllCellsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#cellList.
    def visitCellList(self, ctx:SubaParser.CellListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#variableIdNotation.
    def visitVariableIdNotation(self, ctx:SubaParser.VariableIdNotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#variableIdComponent.
    def visitVariableIdComponent(self, ctx:SubaParser.VariableIdComponentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#indicatorNotation.
    def visitIndicatorNotation(self, ctx:SubaParser.IndicatorNotationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#modifiers.
    def visitModifiers(self, ctx:SubaParser.ModifiersContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#modifierList.
    def visitModifierList(self, ctx:SubaParser.ModifierListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#timeShift.
    def visitTimeShift(self, ctx:SubaParser.TimeShiftContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#timePeriod.
    def visitTimePeriod(self, ctx:SubaParser.TimePeriodContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#consolidationLevel.
    def visitConsolidationLevel(self, ctx:SubaParser.ConsolidationLevelContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#entityReference.
    def visitEntityReference(self, ctx:SubaParser.EntityReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#sdwReference.
    def visitSdwReference(self, ctx:SubaParser.SdwReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#functionCall.
    def visitFunctionCall(self, ctx:SubaParser.FunctionCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#aggregateFunction.
    def visitAggregateFunction(self, ctx:SubaParser.AggregateFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#groupByClause.
    def visitGroupByClause(self, ctx:SubaParser.GroupByClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#unaryMathFunction.
    def visitUnaryMathFunction(self, ctx:SubaParser.UnaryMathFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#binaryMathFunction.
    def visitBinaryMathFunction(self, ctx:SubaParser.BinaryMathFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#variableMathFunction.
    def visitVariableMathFunction(self, ctx:SubaParser.VariableMathFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#stringFunction.
    def visitStringFunction(self, ctx:SubaParser.StringFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#isNullFunction.
    def visitIsNullFunction(self, ctx:SubaParser.IsNullFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#nvlFunction.
    def visitNvlFunction(self, ctx:SubaParser.NvlFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#filterFunction.
    def visitFilterFunction(self, ctx:SubaParser.FilterFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#timeFunction.
    def visitTimeFunction(self, ctx:SubaParser.TimeFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#attributeFunction.
    def visitAttributeFunction(self, ctx:SubaParser.AttributeFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#entityByAttributeFunction.
    def visitEntityByAttributeFunction(self, ctx:SubaParser.EntityByAttributeFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#setExpression.
    def visitSetExpression(self, ctx:SubaParser.SetExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#expressionList.
    def visitExpressionList(self, ctx:SubaParser.ExpressionListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SubaParser#literal.
    def visitLiteral(self, ctx:SubaParser.LiteralContext):
        return self.visitChildren(ctx)



del SubaParser