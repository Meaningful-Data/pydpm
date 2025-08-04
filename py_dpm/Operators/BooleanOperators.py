import operator

from py_dpm.DataTypes.ScalarTypes import Boolean
from py_dpm.Operators import Operator
from py_dpm.Utils import tokens


class Binary(Operator.Binary):
    type_to_check = Boolean


class And(Binary):
    op = tokens.AND
    py_op = operator.and_


class Or(Binary):
    op = tokens.OR
    py_op = operator.or_


class Xor(Binary):
    op = tokens.XOR
    py_op = operator.xor


class Not(Operator.Unary):
    type_to_check = Boolean
    op = tokens.NOT
    py_op = operator.not_
