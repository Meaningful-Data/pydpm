from py_dpm.exceptions.messages import centralised_messages

"""
Exceptions management.
"""


class DrrException(Exception):
    """Base class for exceptions in this module."""

    def __init__(self, message, lino=None, colno=None, code=None):
        if code is not None:
            super().__init__(message, code)
        else:
            super().__init__(message)
        self.lino = lino
        self.colno = colno

    @property
    def pos(self):
        """

        """
        return [self.lino, self.colno]


class SyntaxError(DrrException):

    def __init__(self, code, **kwargs):
        message = centralised_messages[code].format(**kwargs)

        super().__init__(message, None, None, code)


def gather_expression(operand):
    # Lazy import to avoid circular dependency
    from py_dpm.dpm_xl.utils.operands_mapping import LabelHandler

    operands_labels = LabelHandler().operands_labels

    expression = operand
    for key in operands_labels.__reversed__():
        if key in expression:
            expression = expression.replace(key, operands_labels[key])

    if expression is None:
        return expression
    return expression


class SemanticError(DrrException):
    """

    """

    def __init__(self, code, **kwargs):
        # Lazy import to avoid circular dependency
        from py_dpm.dpm_xl.utils.operands_mapping import LabelHandler, get_type_from_label

        operands_labels = LabelHandler().operands_labels
        message = centralised_messages[code].format(**kwargs)
        for operand in reversed(operands_labels):
            if operand in message:
                generated = gather_expression(operand)
                not_single = True if get_type_from_label(operand) == 'not_single' else False
                if not_single:
                    message = message.replace(operand, f"GENERATED:' {generated} '")
                else:
                    message = message.replace(operand, generated)

        super().__init__(message, None, None, code)


class DataTypeError(Exception):
    """

    """

    def __init__(self, value, dataType):
        super().__init__("Invalid Scalar value '{}' for data type {}.".format(
            value, dataType
        ))


class ScriptingError(DrrException):

    def __init__(self, code, **kwargs):
        message = centralised_messages[code].format(**kwargs)
        super().__init__(message, None, None, code)
