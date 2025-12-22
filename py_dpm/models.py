from py_dpm.dpm.db import models as _models

__all__ = [name for name in dir(_models) if not name.startswith("_")]

for name in __all__:
    globals()[name] = getattr(_models, name)
