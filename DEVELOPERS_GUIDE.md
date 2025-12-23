# Developer's Guide

This guide outlines the development patterns and best practices for the PyDPM library.

## Data Models and Serialization

PyDPM uses SQLAlchemy for ORM. To ensure consistency and ease of use, all models should inherit from `SerializationMixin`.

### SerializationMixin

The `SerializationMixin` (in `py_dpm.dpm.db.mixins`) provides a `to_dict()` method that automatically serializes a model instance into a dictionary.

- **Usage**: Ensure your model inherits from `Base` (which includes `SerializationMixin`).
- **API Return Types**: API methods should return `List[Dict[str, Any]]` or `Optional[Dict[str, Any]]` instead of custom dataclasses or Pydantic models.
- **Keys**: The dictionary keys correspond to the model's attribute names (which usually match the database column names).

Example:
```python
# In models.py
class MyModel(Base):
    __tablename__ = "my_table"
    id = Column(Integer, primary_key=True)
    name = Column(String)

# In API
def get_items(self) -> List[Dict[str, Any]]:
    items = self.session.query(MyModel).all()
    return [item.to_dict() for item in items]
```

### Legacy `types.py`

The `py_dpm.api.dpm.types` module has been removed. Do not import from it. Use dictionaries for data exchange.

## Testing

PyDPM uses `pytest` for testing.

### Database Tests

- Use an in-memory SQLite database for testing database interactions.
- Fixtures are available (or should be created) to set up the schema and tear it down.
- Avoid depending on an external running database for unit tests.

### Running Tests

Run tests using Poetry to ensure all dependencies are available:

```bash
poetry run pytest
```
