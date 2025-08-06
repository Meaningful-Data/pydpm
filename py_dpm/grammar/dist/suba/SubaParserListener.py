# Generated from SubaParser.g4 by ANTLR 4.13.1
from antlr4 import *
if "." in __name__:
    from .SubaParser import SubaParser
else:
    from SubaParser import SubaParser

# This class defines a complete listener for a parse tree produced by SubaParser.
class SubaParserListener(ParseTreeListener):

    # Enter a parse tree produced by SubaParser#formula.
    def enterFormula(self, ctx:SubaParser.FormulaContext):
        pass

    # Exit a parse tree produced by SubaParser#formula.
    def exitFormula(self, ctx:SubaParser.FormulaContext):
        pass


    # Enter a parse tree produced by SubaParser#powerExpr.
    def enterPowerExpr(self, ctx:SubaParser.PowerExprContext):
        pass

    # Exit a parse tree produced by SubaParser#powerExpr.
    def exitPowerExpr(self, ctx:SubaParser.PowerExprContext):
        pass


    # Enter a parse tree produced by SubaParser#dataPointExpr.
    def enterDataPointExpr(self, ctx:SubaParser.DataPointExprContext):
        pass

    # Exit a parse tree produced by SubaParser#dataPointExpr.
    def exitDataPointExpr(self, ctx:SubaParser.DataPointExprContext):
        pass


    # Enter a parse tree produced by SubaParser#sdwExpr.
    def enterSdwExpr(self, ctx:SubaParser.SdwExprContext):
        pass

    # Exit a parse tree produced by SubaParser#sdwExpr.
    def exitSdwExpr(self, ctx:SubaParser.SdwExprContext):
        pass


    # Enter a parse tree produced by SubaParser#inExpr.
    def enterInExpr(self, ctx:SubaParser.InExprContext):
        pass

    # Exit a parse tree produced by SubaParser#inExpr.
    def exitInExpr(self, ctx:SubaParser.InExprContext):
        pass


    # Enter a parse tree produced by SubaParser#logicalExpr.
    def enterLogicalExpr(self, ctx:SubaParser.LogicalExprContext):
        pass

    # Exit a parse tree produced by SubaParser#logicalExpr.
    def exitLogicalExpr(self, ctx:SubaParser.LogicalExprContext):
        pass


    # Enter a parse tree produced by SubaParser#comparisonExpr.
    def enterComparisonExpr(self, ctx:SubaParser.ComparisonExprContext):
        pass

    # Exit a parse tree produced by SubaParser#comparisonExpr.
    def exitComparisonExpr(self, ctx:SubaParser.ComparisonExprContext):
        pass


    # Enter a parse tree produced by SubaParser#additiveExpr.
    def enterAdditiveExpr(self, ctx:SubaParser.AdditiveExprContext):
        pass

    # Exit a parse tree produced by SubaParser#additiveExpr.
    def exitAdditiveExpr(self, ctx:SubaParser.AdditiveExprContext):
        pass


    # Enter a parse tree produced by SubaParser#functionExpr.
    def enterFunctionExpr(self, ctx:SubaParser.FunctionExprContext):
        pass

    # Exit a parse tree produced by SubaParser#functionExpr.
    def exitFunctionExpr(self, ctx:SubaParser.FunctionExprContext):
        pass


    # Enter a parse tree produced by SubaParser#concatExpr.
    def enterConcatExpr(self, ctx:SubaParser.ConcatExprContext):
        pass

    # Exit a parse tree produced by SubaParser#concatExpr.
    def exitConcatExpr(self, ctx:SubaParser.ConcatExprContext):
        pass


    # Enter a parse tree produced by SubaParser#notExpr.
    def enterNotExpr(self, ctx:SubaParser.NotExprContext):
        pass

    # Exit a parse tree produced by SubaParser#notExpr.
    def exitNotExpr(self, ctx:SubaParser.NotExprContext):
        pass


    # Enter a parse tree produced by SubaParser#unaryExpr.
    def enterUnaryExpr(self, ctx:SubaParser.UnaryExprContext):
        pass

    # Exit a parse tree produced by SubaParser#unaryExpr.
    def exitUnaryExpr(self, ctx:SubaParser.UnaryExprContext):
        pass


    # Enter a parse tree produced by SubaParser#parenthesizedExpr.
    def enterParenthesizedExpr(self, ctx:SubaParser.ParenthesizedExprContext):
        pass

    # Exit a parse tree produced by SubaParser#parenthesizedExpr.
    def exitParenthesizedExpr(self, ctx:SubaParser.ParenthesizedExprContext):
        pass


    # Enter a parse tree produced by SubaParser#literalExpr.
    def enterLiteralExpr(self, ctx:SubaParser.LiteralExprContext):
        pass

    # Exit a parse tree produced by SubaParser#literalExpr.
    def exitLiteralExpr(self, ctx:SubaParser.LiteralExprContext):
        pass


    # Enter a parse tree produced by SubaParser#listExpr.
    def enterListExpr(self, ctx:SubaParser.ListExprContext):
        pass

    # Exit a parse tree produced by SubaParser#listExpr.
    def exitListExpr(self, ctx:SubaParser.ListExprContext):
        pass


    # Enter a parse tree produced by SubaParser#multiplicativeExpr.
    def enterMultiplicativeExpr(self, ctx:SubaParser.MultiplicativeExprContext):
        pass

    # Exit a parse tree produced by SubaParser#multiplicativeExpr.
    def exitMultiplicativeExpr(self, ctx:SubaParser.MultiplicativeExprContext):
        pass


    # Enter a parse tree produced by SubaParser#conditionalExpr.
    def enterConditionalExpr(self, ctx:SubaParser.ConditionalExprContext):
        pass

    # Exit a parse tree produced by SubaParser#conditionalExpr.
    def exitConditionalExpr(self, ctx:SubaParser.ConditionalExprContext):
        pass


    # Enter a parse tree produced by SubaParser#codeExpr.
    def enterCodeExpr(self, ctx:SubaParser.CodeExprContext):
        pass

    # Exit a parse tree produced by SubaParser#codeExpr.
    def exitCodeExpr(self, ctx:SubaParser.CodeExprContext):
        pass


    # Enter a parse tree produced by SubaParser#comparisonOp.
    def enterComparisonOp(self, ctx:SubaParser.ComparisonOpContext):
        pass

    # Exit a parse tree produced by SubaParser#comparisonOp.
    def exitComparisonOp(self, ctx:SubaParser.ComparisonOpContext):
        pass


    # Enter a parse tree produced by SubaParser#dataPointReference.
    def enterDataPointReference(self, ctx:SubaParser.DataPointReferenceContext):
        pass

    # Exit a parse tree produced by SubaParser#dataPointReference.
    def exitDataPointReference(self, ctx:SubaParser.DataPointReferenceContext):
        pass


    # Enter a parse tree produced by SubaParser#dataArea.
    def enterDataArea(self, ctx:SubaParser.DataAreaContext):
        pass

    # Exit a parse tree produced by SubaParser#dataArea.
    def exitDataArea(self, ctx:SubaParser.DataAreaContext):
        pass


    # Enter a parse tree produced by SubaParser#dataPointSpec.
    def enterDataPointSpec(self, ctx:SubaParser.DataPointSpecContext):
        pass

    # Exit a parse tree produced by SubaParser#dataPointSpec.
    def exitDataPointSpec(self, ctx:SubaParser.DataPointSpecContext):
        pass


    # Enter a parse tree produced by SubaParser#tsrcNotation.
    def enterTsrcNotation(self, ctx:SubaParser.TsrcNotationContext):
        pass

    # Exit a parse tree produced by SubaParser#tsrcNotation.
    def exitTsrcNotation(self, ctx:SubaParser.TsrcNotationContext):
        pass


    # Enter a parse tree produced by SubaParser#tableComponent.
    def enterTableComponent(self, ctx:SubaParser.TableComponentContext):
        pass

    # Exit a parse tree produced by SubaParser#tableComponent.
    def exitTableComponent(self, ctx:SubaParser.TableComponentContext):
        pass


    # Enter a parse tree produced by SubaParser#sheetComponent.
    def enterSheetComponent(self, ctx:SubaParser.SheetComponentContext):
        pass

    # Exit a parse tree produced by SubaParser#sheetComponent.
    def exitSheetComponent(self, ctx:SubaParser.SheetComponentContext):
        pass


    # Enter a parse tree produced by SubaParser#rowComponent.
    def enterRowComponent(self, ctx:SubaParser.RowComponentContext):
        pass

    # Exit a parse tree produced by SubaParser#rowComponent.
    def exitRowComponent(self, ctx:SubaParser.RowComponentContext):
        pass


    # Enter a parse tree produced by SubaParser#columnComponent.
    def enterColumnComponent(self, ctx:SubaParser.ColumnComponentContext):
        pass

    # Exit a parse tree produced by SubaParser#columnComponent.
    def exitColumnComponent(self, ctx:SubaParser.ColumnComponentContext):
        pass


    # Enter a parse tree produced by SubaParser#tableCode.
    def enterTableCode(self, ctx:SubaParser.TableCodeContext):
        pass

    # Exit a parse tree produced by SubaParser#tableCode.
    def exitTableCode(self, ctx:SubaParser.TableCodeContext):
        pass


    # Enter a parse tree produced by SubaParser#singleCell.
    def enterSingleCell(self, ctx:SubaParser.SingleCellContext):
        pass

    # Exit a parse tree produced by SubaParser#singleCell.
    def exitSingleCell(self, ctx:SubaParser.SingleCellContext):
        pass


    # Enter a parse tree produced by SubaParser#rangeCell.
    def enterRangeCell(self, ctx:SubaParser.RangeCellContext):
        pass

    # Exit a parse tree produced by SubaParser#rangeCell.
    def exitRangeCell(self, ctx:SubaParser.RangeCellContext):
        pass


    # Enter a parse tree produced by SubaParser#allCells.
    def enterAllCells(self, ctx:SubaParser.AllCellsContext):
        pass

    # Exit a parse tree produced by SubaParser#allCells.
    def exitAllCells(self, ctx:SubaParser.AllCellsContext):
        pass


    # Enter a parse tree produced by SubaParser#cellList.
    def enterCellList(self, ctx:SubaParser.CellListContext):
        pass

    # Exit a parse tree produced by SubaParser#cellList.
    def exitCellList(self, ctx:SubaParser.CellListContext):
        pass


    # Enter a parse tree produced by SubaParser#cellCode.
    def enterCellCode(self, ctx:SubaParser.CellCodeContext):
        pass

    # Exit a parse tree produced by SubaParser#cellCode.
    def exitCellCode(self, ctx:SubaParser.CellCodeContext):
        pass


    # Enter a parse tree produced by SubaParser#variableIdNotation.
    def enterVariableIdNotation(self, ctx:SubaParser.VariableIdNotationContext):
        pass

    # Exit a parse tree produced by SubaParser#variableIdNotation.
    def exitVariableIdNotation(self, ctx:SubaParser.VariableIdNotationContext):
        pass


    # Enter a parse tree produced by SubaParser#variableIdComponent.
    def enterVariableIdComponent(self, ctx:SubaParser.VariableIdComponentContext):
        pass

    # Exit a parse tree produced by SubaParser#variableIdComponent.
    def exitVariableIdComponent(self, ctx:SubaParser.VariableIdComponentContext):
        pass


    # Enter a parse tree produced by SubaParser#indicatorNotation.
    def enterIndicatorNotation(self, ctx:SubaParser.IndicatorNotationContext):
        pass

    # Exit a parse tree produced by SubaParser#indicatorNotation.
    def exitIndicatorNotation(self, ctx:SubaParser.IndicatorNotationContext):
        pass


    # Enter a parse tree produced by SubaParser#modifiers.
    def enterModifiers(self, ctx:SubaParser.ModifiersContext):
        pass

    # Exit a parse tree produced by SubaParser#modifiers.
    def exitModifiers(self, ctx:SubaParser.ModifiersContext):
        pass


    # Enter a parse tree produced by SubaParser#modifierList.
    def enterModifierList(self, ctx:SubaParser.ModifierListContext):
        pass

    # Exit a parse tree produced by SubaParser#modifierList.
    def exitModifierList(self, ctx:SubaParser.ModifierListContext):
        pass


    # Enter a parse tree produced by SubaParser#timeShift.
    def enterTimeShift(self, ctx:SubaParser.TimeShiftContext):
        pass

    # Exit a parse tree produced by SubaParser#timeShift.
    def exitTimeShift(self, ctx:SubaParser.TimeShiftContext):
        pass


    # Enter a parse tree produced by SubaParser#timePeriod.
    def enterTimePeriod(self, ctx:SubaParser.TimePeriodContext):
        pass

    # Exit a parse tree produced by SubaParser#timePeriod.
    def exitTimePeriod(self, ctx:SubaParser.TimePeriodContext):
        pass


    # Enter a parse tree produced by SubaParser#consolidationLevel.
    def enterConsolidationLevel(self, ctx:SubaParser.ConsolidationLevelContext):
        pass

    # Exit a parse tree produced by SubaParser#consolidationLevel.
    def exitConsolidationLevel(self, ctx:SubaParser.ConsolidationLevelContext):
        pass


    # Enter a parse tree produced by SubaParser#entityReference.
    def enterEntityReference(self, ctx:SubaParser.EntityReferenceContext):
        pass

    # Exit a parse tree produced by SubaParser#entityReference.
    def exitEntityReference(self, ctx:SubaParser.EntityReferenceContext):
        pass


    # Enter a parse tree produced by SubaParser#sdwReference.
    def enterSdwReference(self, ctx:SubaParser.SdwReferenceContext):
        pass

    # Exit a parse tree produced by SubaParser#sdwReference.
    def exitSdwReference(self, ctx:SubaParser.SdwReferenceContext):
        pass


    # Enter a parse tree produced by SubaParser#functionCall.
    def enterFunctionCall(self, ctx:SubaParser.FunctionCallContext):
        pass

    # Exit a parse tree produced by SubaParser#functionCall.
    def exitFunctionCall(self, ctx:SubaParser.FunctionCallContext):
        pass


    # Enter a parse tree produced by SubaParser#aggregateFunction.
    def enterAggregateFunction(self, ctx:SubaParser.AggregateFunctionContext):
        pass

    # Exit a parse tree produced by SubaParser#aggregateFunction.
    def exitAggregateFunction(self, ctx:SubaParser.AggregateFunctionContext):
        pass


    # Enter a parse tree produced by SubaParser#groupByClause.
    def enterGroupByClause(self, ctx:SubaParser.GroupByClauseContext):
        pass

    # Exit a parse tree produced by SubaParser#groupByClause.
    def exitGroupByClause(self, ctx:SubaParser.GroupByClauseContext):
        pass


    # Enter a parse tree produced by SubaParser#unaryMathFunction.
    def enterUnaryMathFunction(self, ctx:SubaParser.UnaryMathFunctionContext):
        pass

    # Exit a parse tree produced by SubaParser#unaryMathFunction.
    def exitUnaryMathFunction(self, ctx:SubaParser.UnaryMathFunctionContext):
        pass


    # Enter a parse tree produced by SubaParser#binaryMathFunction.
    def enterBinaryMathFunction(self, ctx:SubaParser.BinaryMathFunctionContext):
        pass

    # Exit a parse tree produced by SubaParser#binaryMathFunction.
    def exitBinaryMathFunction(self, ctx:SubaParser.BinaryMathFunctionContext):
        pass


    # Enter a parse tree produced by SubaParser#variableMathFunction.
    def enterVariableMathFunction(self, ctx:SubaParser.VariableMathFunctionContext):
        pass

    # Exit a parse tree produced by SubaParser#variableMathFunction.
    def exitVariableMathFunction(self, ctx:SubaParser.VariableMathFunctionContext):
        pass


    # Enter a parse tree produced by SubaParser#stringFunction.
    def enterStringFunction(self, ctx:SubaParser.StringFunctionContext):
        pass

    # Exit a parse tree produced by SubaParser#stringFunction.
    def exitStringFunction(self, ctx:SubaParser.StringFunctionContext):
        pass


    # Enter a parse tree produced by SubaParser#isNullFunction.
    def enterIsNullFunction(self, ctx:SubaParser.IsNullFunctionContext):
        pass

    # Exit a parse tree produced by SubaParser#isNullFunction.
    def exitIsNullFunction(self, ctx:SubaParser.IsNullFunctionContext):
        pass


    # Enter a parse tree produced by SubaParser#nvlFunction.
    def enterNvlFunction(self, ctx:SubaParser.NvlFunctionContext):
        pass

    # Exit a parse tree produced by SubaParser#nvlFunction.
    def exitNvlFunction(self, ctx:SubaParser.NvlFunctionContext):
        pass


    # Enter a parse tree produced by SubaParser#filterFunction.
    def enterFilterFunction(self, ctx:SubaParser.FilterFunctionContext):
        pass

    # Exit a parse tree produced by SubaParser#filterFunction.
    def exitFilterFunction(self, ctx:SubaParser.FilterFunctionContext):
        pass


    # Enter a parse tree produced by SubaParser#timeShiftFunction.
    def enterTimeShiftFunction(self, ctx:SubaParser.TimeShiftFunctionContext):
        pass

    # Exit a parse tree produced by SubaParser#timeShiftFunction.
    def exitTimeShiftFunction(self, ctx:SubaParser.TimeShiftFunctionContext):
        pass


    # Enter a parse tree produced by SubaParser#datetimeFunction.
    def enterDatetimeFunction(self, ctx:SubaParser.DatetimeFunctionContext):
        pass

    # Exit a parse tree produced by SubaParser#datetimeFunction.
    def exitDatetimeFunction(self, ctx:SubaParser.DatetimeFunctionContext):
        pass


    # Enter a parse tree produced by SubaParser#logicalFunctionCall.
    def enterLogicalFunctionCall(self, ctx:SubaParser.LogicalFunctionCallContext):
        pass

    # Exit a parse tree produced by SubaParser#logicalFunctionCall.
    def exitLogicalFunctionCall(self, ctx:SubaParser.LogicalFunctionCallContext):
        pass


    # Enter a parse tree produced by SubaParser#attributeFunction.
    def enterAttributeFunction(self, ctx:SubaParser.AttributeFunctionContext):
        pass

    # Exit a parse tree produced by SubaParser#attributeFunction.
    def exitAttributeFunction(self, ctx:SubaParser.AttributeFunctionContext):
        pass


    # Enter a parse tree produced by SubaParser#entityByAttributeFunction.
    def enterEntityByAttributeFunction(self, ctx:SubaParser.EntityByAttributeFunctionContext):
        pass

    # Exit a parse tree produced by SubaParser#entityByAttributeFunction.
    def exitEntityByAttributeFunction(self, ctx:SubaParser.EntityByAttributeFunctionContext):
        pass


    # Enter a parse tree produced by SubaParser#setExpression.
    def enterSetExpression(self, ctx:SubaParser.SetExpressionContext):
        pass

    # Exit a parse tree produced by SubaParser#setExpression.
    def exitSetExpression(self, ctx:SubaParser.SetExpressionContext):
        pass


    # Enter a parse tree produced by SubaParser#expressionList.
    def enterExpressionList(self, ctx:SubaParser.ExpressionListContext):
        pass

    # Exit a parse tree produced by SubaParser#expressionList.
    def exitExpressionList(self, ctx:SubaParser.ExpressionListContext):
        pass


    # Enter a parse tree produced by SubaParser#literal.
    def enterLiteral(self, ctx:SubaParser.LiteralContext):
        pass

    # Exit a parse tree produced by SubaParser#literal.
    def exitLiteral(self, ctx:SubaParser.LiteralContext):
        pass



del SubaParser