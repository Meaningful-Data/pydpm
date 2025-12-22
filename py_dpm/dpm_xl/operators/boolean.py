import operator

from py_dpm.dpm_xl.types.scalar import Boolean
from py_dpm.dpm_xl.operators.base import Operator, Binary, Unary, Complex
from py_dpm.dpm_xl.utils import tokens


class Binary(Binary):
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


class Not(Unary):
    type_to_check = Boolean
    op = tokens.NOT
    py_op = operator.not_
