from aries_cloudagent.utils.json import JsonUtil


def test_format_json():
    # Test format_json with different types to ensure whitespace is corrrectly re-added
    json_str = '{"key":"value","key2":"value2"}'
    formatted_json_str = JsonUtil.format_json(json_str)
    assert formatted_json_str == '{"key": "value", "key2": "value2"}'

    # Test with string value
    json_str = '{"key":"value"}'
    formatted_json_str = JsonUtil.format_json(json_str)
    assert formatted_json_str == '{"key": "value"}'

    # Test with numeric value
    json_str = '{"key":1}'
    formatted_json_str = JsonUtil.format_json(json_str)
    assert formatted_json_str == '{"key": 1}'

    # Test with JSON object value
    json_str = '{"key":{"subkey":"value"}}'
    formatted_json_str = JsonUtil.format_json(json_str)
    assert formatted_json_str == '{"key": {"subkey": "value"}}'

    # Test with list value
    json_str = '{"key":["value1","value2"]}'
    formatted_json_str = JsonUtil.format_json(json_str)
    assert formatted_json_str == '{"key": ["value1", "value2"]}'

    # Test with boolean value
    json_str = '{"key":true}'
    formatted_json_str = JsonUtil.format_json(json_str)
    assert formatted_json_str == '{"key": true}'

    # Test with null value
    json_str = '{"key":null}'
    formatted_json_str = JsonUtil.format_json(json_str)
    assert formatted_json_str == '{"key": null}'


def test_dumps():
    # Test the dumps method
    obj = {"key": "value", "key2": "value2"}
    json_str = JsonUtil.dumps(obj)
    assert json_str == '{"key": "value", "key2": "value2"}'


def test_dumps_w_indent():
    # Test the dumps method
    obj = {"key": "value", "key2": "value2"}
    json_str = JsonUtil.dumps(obj, indent=4)
    assert json_str == '{\n    "key": "value",\n    "key2": "value2"\n}'


def test_loads():
    # Test the loads method
    json_str = '{"key": "value", "key2": "value2"}'
    obj = JsonUtil.loads(json_str)
    assert obj == {"key": "value", "key2": "value2"}


def test_loads_wo_spaces():
    # Test the loads method
    json_str = '{"key":"value","key2":"value2"}'
    obj = JsonUtil.loads(json_str)
    assert obj == {"key": "value", "key2": "value2"}
