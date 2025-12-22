import operator

from py_dpm.dpm_xl.types.scalar import Integer, String
from py_dpm.dpm_xl.operators.base import Operator, Binary, Unary, Complex
from py_dpm.dpm_xl.utils import tokens


class Unary(Unary):
    op = None
    type_to_check = String


class Binary(Binary):
    op = None
    type_to_check = String


class Len(Unary):
    op = tokens.LENGTH
    py_op = operator.length_hint
    return_type = Integer


class Concatenate(Binary):
    op = tokens.CONCATENATE
    py_op = operator.concat
    return_type = String
