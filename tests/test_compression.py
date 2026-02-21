import base64
import gzip
import json
import os
import shutil
from unittest.mock import MagicMock, patch

import pytest

from cacherator import JSONCache, Cached
from cacherator.cacherator import _DYNAMODB_COMPRESS_THRESHOLD, _DYNAMODB_MAX_SIZE


class CachedClass(JSONCache):
    def __init__(self, **kwargs):
        super().__init__(data_id="test_compression", directory="test_cache", logging=False, **kwargs)

    @Cached()
    def compute(self, x):
        return x * 2


@pytest.fixture(autouse=True)
def cleanup():
    test_dir = "test_cache"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    yield
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


@pytest.fixture
def obj_with_mock_dynamodb():
    obj = CachedClass()
    obj._dynamodb = MagicMock()
    obj._dynamodb_enabled = True
    return obj


class TestCompression:

    def test_small_payload_not_compressed(self, obj_with_mock_dynamodb):
        obj = obj_with_mock_dynamodb
        obj.compute(1)
        obj._write_to_dynamodb()

        call_args = obj._dynamodb.put.call_args
        stored_data = call_args[0][1]
        assert "_compressed" not in stored_data

    def test_large_payload_is_compressed(self, obj_with_mock_dynamodb):
        obj = obj_with_mock_dynamodb
        obj.large_data = "x" * _DYNAMODB_COMPRESS_THRESHOLD
        obj._write_to_dynamodb()

        call_args = obj._dynamodb.put.call_args
        stored_data = call_args[0][1]
        assert stored_data.get("_compressed") is True
        assert "data" in stored_data

    def test_compressed_data_is_valid_gzip(self, obj_with_mock_dynamodb):
        obj = obj_with_mock_dynamodb
        obj.large_data = "x" * _DYNAMODB_COMPRESS_THRESHOLD
        obj._write_to_dynamodb()

        stored_data = obj._dynamodb.put.call_args[0][1]
        raw = base64.b64decode(stored_data["data"])
        decompressed = gzip.decompress(raw)
        parsed = json.loads(decompressed.decode())
        assert "_json_cache_func_cache" in parsed

    def test_compressed_roundtrip(self, obj_with_mock_dynamodb):
        obj = obj_with_mock_dynamodb
        obj.large_data = "x" * _DYNAMODB_COMPRESS_THRESHOLD
        obj._write_to_dynamodb()

        stored_data = obj._dynamodb.put.call_args[0][1]
        obj._dynamodb.get.return_value = stored_data
        result = obj._load_from_dynamodb()

        assert "_json_cache_func_cache" in result
        assert result["_json_cache_variable_cache"]["large_data"] == "x" * _DYNAMODB_COMPRESS_THRESHOLD

    def test_uncompressed_roundtrip(self, obj_with_mock_dynamodb):
        obj = obj_with_mock_dynamodb
        obj.compute(42)
        obj._write_to_dynamodb()

        stored_data = obj._dynamodb.put.call_args[0][1]
        obj._dynamodb.get.return_value = stored_data
        result = obj._load_from_dynamodb()

        assert "_json_cache_func_cache" in result

    def test_oversized_payload_not_written(self, obj_with_mock_dynamodb):
        obj = obj_with_mock_dynamodb
        # Use incompressible random-ish data to stay large after gzip
        obj.large_data = list(range(_DYNAMODB_MAX_SIZE // 4))

        with patch("cacherator.cacherator.gzip.compress") as mock_compress:
            mock_compress.return_value = b"x" * (_DYNAMODB_MAX_SIZE + 1)
            obj._write_to_dynamodb()

        obj._dynamodb.put.assert_not_called()

    def test_compression_log_message(self, obj_with_mock_dynamodb, capsys):
        obj = obj_with_mock_dynamodb
        obj._json_cache_logging = True
        obj.large_data = "x" * _DYNAMODB_COMPRESS_THRESHOLD

        with patch("cacherator.cacherator.Logger.note") as mock_note:
            obj._write_to_dynamodb()
            assert mock_note.called
            log_msg = mock_note.call_args[0][0]
            assert "Compressing" in log_msg

    def test_oversized_warning_logged(self, obj_with_mock_dynamodb):
        obj = obj_with_mock_dynamodb
        obj.large_data = "x" * _DYNAMODB_COMPRESS_THRESHOLD

        with patch("cacherator.cacherator.gzip.compress") as mock_compress, \
             patch("cacherator.cacherator.Logger.note") as mock_note:
            mock_compress.return_value = b"x" * (_DYNAMODB_MAX_SIZE + 1)
            obj._write_to_dynamodb()

            warning_calls = [c for c in mock_note.call_args_list if "WARNING" in c[0][0]]
            assert len(warning_calls) == 1
