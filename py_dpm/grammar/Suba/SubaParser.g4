parser grammar SubaParser;

options { tokenVocab=SubaLexer; }

// Entry point
formula: expression (comparisonOp expression)? EOF;

expression:
    expression op=(MULT | DIV) expression                              # multiplicativeExpr
    | expression op=(PLUS | MINUS) expression                          # additiveExpr
    | expression POWER expression                                      # powerExpr
    | expression CONCAT expression                                     # concatExpr
    | expression comparisonOp expression                               # comparisonExpr
    | expression op=(AND | OR | XOR) expression                        # logicalExpr
    | expression IN setExpression                                      # inExpr
    | NOT expression                                                   # notExpr
    | op=(PLUS | MINUS) expression                                     # unaryExpr
    | IF expression THEN expression (ELSE expression)? ENDIF           # conditionalExpr
    | functionCall                                                     # functionExpr
    | dataPointReference                                               # dataPointExpr
    | sdwReference                                                     # sdwExpr
    | literal                                                          # literalExpr
    | CODE                                                             # codeExpr
    | LPAREN expression RPAREN                                         # parenthesizedExpr
    | LBRACKET expressionList RBRACKET                                # listExpr
    ;

comparisonOp:
    EQ | NE | LT | LE | GT | GE
    ;

dataPointReference:
    LBRACE dataArea? dataPointSpec modifiers? RBRACE
    ;

dataArea:
    (EBA_ITS | SRB_LDT | IMAS_PROD | IMAS_IND) DOT
    ;

dataPointSpec:
    tsrcNotation
    | variableIdNotation
    | indicatorNotation
    ;

tsrcNotation:
    tsrcComponent+
    ;

tsrcComponent:
    T LPAREN tableCode RPAREN                                         # tableComponent
    | S LPAREN cellSpecifier RPAREN                                   # sheetComponent
    | R LPAREN cellSpecifier RPAREN                                   # rowComponent
    | C LPAREN cellSpecifier RPAREN                                   # columnComponent
    ;

tableCode:
    CODE    // Will match C_01.00, C_17.01.a, Z_03.01, etc.
    ;

cellSpecifier:
    cellCode                                                           # singleCell
    | cellCode MINUS cellCode                                         # rangeCell
    | MULT                                                            # allCells
    | cellCode (COMMA cellCode)+                                      # cellList
    ;

cellCode:
    CODE | INTEGER_LITERAL
    ;

variableIdNotation:
    (XBRL | VAR) COLON variableIdComponent+
    ;

variableIdComponent:
    CODE (LPAREN CODE RPAREN)?
    ;

indicatorNotation:
    CODE
    ;

modifiers:
    LBRACKET modifierList RBRACKET
    ;

modifierList:
    timeShift? (SEMICOLON consolidationLevel)? (SEMICOLON entityReference)?
    ;

timeShift:
    T (PLUS | MINUS) INTEGER_LITERAL timePeriod
    ;

timePeriod:
    TIME_PERIOD_YEAR
    | TIME_PERIOD_QUARTER
    | TIME_PERIOD_MONTH
    | TIME_PERIOD_WEEK
    | TIME_PERIOD_DAY
    ;

consolidationLevel:
    STRING_LITERAL
    | HIGHEST
    | attributeFunction
    ;

entityReference:
    STRING_LITERAL
    | entityByAttributeFunction
    ;

sdwReference:
    SDW DOT CODE
    ;

functionCall:
    aggregateFunction
    | mathFunction
    | stringFunction
    | nullFunction
    | filterFunction
    | timeFunction
    | logicalFunction
    ;

aggregateFunction:
    (SUM | AVG | COUNT | MAX | MIN | MEDIAN)
    LPAREN expression (COMMA groupByClause)? RPAREN
    ;

groupByClause:
    GROUP_BY CODE (COMMA CODE)*
    ;

mathFunction:
    (ABS | EXP | LN | SQRT) LPAREN expression RPAREN                  # unaryMathFunction
    | (LOG | POWER) LPAREN expression COMMA expression RPAREN         # binaryMathFunction
    | (MAX | MIN) LPAREN expressionList RPAREN                        # variableMathFunction
    ;

stringFunction:
    LEN LPAREN expression RPAREN
    ;

nullFunction:
    ISNULL LPAREN expression RPAREN                                   # isNullFunction
    | NVL LPAREN expression COMMA expression RPAREN                   # nvlFunction
    ;

filterFunction:
    FILTER LPAREN expression COMMA expression RPAREN
    ;

timeFunction:
    TIME_SHIFT LPAREN expression COMMA timePeriod COMMA
    INTEGER_LITERAL (COMMA CODE)? RPAREN                              # timeShiftFunction
    | DATETIME LPAREN STRING_LITERAL RPAREN                           # datetimeFunction
    ;

logicalFunction:
    LOGICAL LPAREN expression RPAREN                                  # logicalFunctionCall
    ;

attributeFunction:
    ATTRIBUTE LPAREN STRING_LITERAL COMMA STRING_LITERAL RPAREN
    ;

entityByAttributeFunction:
    ENTITY_BY_ATTRIBUTE LPAREN STRING_LITERAL COMMA STRING_LITERAL RPAREN
    ;

setExpression:
    LBRACE expressionList RBRACE
    ;

expressionList:
    expression (COMMA expression)*
    ;

literal:
    BOOLEAN_LITERAL
    | NULL_LITERAL
    | INTEGER_LITERAL
    | DECIMAL_LITERAL
    | PERCENT_LITERAL
    | STRING_LITERAL
    ;