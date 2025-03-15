from uplan.utils.text import extract_code_block


def test_code_block_with_language():
    doc = "Some text\n```python\nprint('Hello world')\n```"
    result = extract_code_block(doc)
    expected = "print('Hello world')"
    assert result == expected


def test_code_block_without_language():
    doc = "Header\n```\nprint('Test')\n```"
    result = extract_code_block(doc)
    expected = "print('Test')"
    assert result == expected


def test_no_code_block():
    doc = "This is a test without code block"
    result = extract_code_block(doc)
    assert result is None


def test_empty_code_block():
    doc = "```\n\n```"
    result = extract_code_block(doc)
    assert result == ""
