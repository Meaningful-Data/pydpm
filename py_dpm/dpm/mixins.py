from sqlalchemy.inspection import inspect


class SerializationMixin:
    """Mixin to add serialization capabilities to SQLAlchemy models."""

    def to_dict(self):
        """Convert the model instance to a dictionary."""
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
