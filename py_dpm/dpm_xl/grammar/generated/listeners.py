from antlr4.error.ErrorListener import ErrorListener


class DPMErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        # UTILS_UTILS.1
        raise SyntaxError('offendingSymbol: {} msg: {}'.format(offendingSymbol, msg))
