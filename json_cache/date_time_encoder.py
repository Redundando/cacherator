from json import JSONEncoder
from datetime import datetime

class DateTimeEncoder(JSONEncoder):
    """
    Custom JSON encoder that extends `json.JSONEncoder` to handle additional data types.

    This encoder specifically supports:
    - `datetime.datetime`: Serialized into ISO 8601 string format (`YYYY-MM-DDTHH:MM:SS.ssssss`).

    Use this encoder to ensure objects containing `datetime` instances can be serialized
    into JSON without additional preprocessing.

    Example:
        import json
        from datetime import datetime

        data = {"timestamp": datetime.now()}
        json_string = json.dumps(data, cls=DateTimeEncoder)
        # Output: '{"timestamp": "2024-11-21T10:15:30.123456"}'

    Methods:
        default(o): Converts unsupported objects (e.g., `datetime.datetime`)
                    into a JSON-serializable format.
    """

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return JSONEncoder.default(self, o)