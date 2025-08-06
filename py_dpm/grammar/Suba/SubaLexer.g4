lexer grammar SUBALexer;

// ------------ Operators -----------

// Boolean
AND:                    'AND';
OR:                     'OR';
NOT:                    'NOT';
XOR:                    'XOR';

// Arithmetic
PLUS:                   '+';
MINUS:                  '-';
MULT:                   '*';
DIV:                    '/';
POWER:                  '**';

// Comparison
EQ:                     '=' | '==' | 'EQ';
NE:                     '^=' | 'NE';
LT:                     '<' | 'LT';
LE:                     '<=' | 'LE';
GT:                     '>' | 'GT';
GE:                     '>=' | 'GE';

// Set operations
IN:                     'IN';
INCLUDES:               'includes';

// Aggregate functions
SUM:                    'SUM';
AVG:                    'AVG';
COUNT:                  'COUNT';
MAX:                    'MAX';
MIN:                    'MIN';
MEDIAN:                 'MEDIAN';

// Math functions
ABS:                    'ABS';
EXP:                    'EXP';
LN:                     'LN';
SQRT:                   'SQRT';
LOG:                    'LOG';

// String functions
LEN:                    'LEN';
CONCAT:                 '&';

// Conditional
IF:                     'IF';
THEN:                   'THEN';
ELSE:                   'ELSE';
ENDIF:                  'ENDIF';
NVL:                    'NVL';
ISNULL:                 'ISNULL';

// Time functions
TIME_SHIFT:             'TIME_SHIFT';

// Filter operations
FILTER:                 'FILTER';
WHERE:                  'WHERE';
MATCH:                  'MATCH';

// Prefixes for data areas
EBA_ITS:                'EBA_ITS';
SRB_LDT:                'SRB_LDT';
IMAS_PROD:              'IMAS_PROD';
IMAS_IND:               'IMAS_IND';
SDW:                    'SDW';

// Variable ID prefix
XBRL:                   'XBRL';
VAR:                    'VAR';

// Special keywords
HIGHEST:                'HIGHEST';
ATTRIBUTE:              'ATTRIBUTE';
ENTITY_BY_ATTRIBUTE:    'ENTITY_BY_ATTRIBUTE';
GROUP_BY:               'GROUP_BY';

// Time period indicators
TIME_PERIOD_YEAR:       'Y';
TIME_PERIOD_QUARTER:    'Q';
TIME_PERIOD_MONTH:      'M';
TIME_PERIOD_WEEK:       'W';
TIME_PERIOD_DAY:        'D';

// TSRC Component prefixes
T:                      'T';
S:                      'S';
R:                      'R';
C:                      'C';

// Punctuation
LPAREN:                 '(';
RPAREN:                 ')';
LBRACE:                 '{';
RBRACE:                 '}';
LBRACKET:               '[';
RBRACKET:               ']';
COMMA:                  ',';
SEMICOLON:              ';';
COLON:                  ':';
DOT:                    '.';
QUOTE:                  '\'';

// Literals
BOOLEAN_LITERAL:        'true' | 'false';
NULL_LITERAL:           'null';
STRING_LITERAL:         '"' (~["\r\n])* '"' | '\'' (~['\r\n])* '\'';

// These must come AFTER keywords but BEFORE CODE
// Code patterns (matches table codes, cell codes, identifiers)
// Includes patterns like: C_01.00, 0130, 0010-0080, ABC, etc.
CODE:                   (LETTER | DIGIT) (LETTER | DIGIT | '_' | '.' | '-')*;

// Numeric literals - must come AFTER CODE to avoid taking precedence
INTEGER_LITERAL:        '-'? DIGIT+ { !Character.isLetter(_input.LA(1)) && _input.LA(1) != '_' && _input.LA(1) != '.' && _input.LA(1) != '-' }?;
DECIMAL_LITERAL:        '-'? DIGIT+ '.' DIGIT+;
PERCENT_LITERAL:        '-'? (DIGIT+ ('.' DIGIT+)?) '%';

// Whitespace
WS:                     [ \t\r\n]+ -> skip;

// Fragments
fragment DIGIT:         [0-9];
fragment LETTER:        [a-zA-Z];