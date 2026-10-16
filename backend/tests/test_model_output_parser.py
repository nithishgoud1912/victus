import json

import pytest

from victus.agent.output_parser import ActionDecision, FinishDecision, OutputParser
from victus.models.contracts import ErrorCode, ModelError
from victus.tools.contracts import NoteArguments


@pytest.fixture
def parser():
    return OutputParser({"fs.create_note": NoteArguments})


def action(**updates):
    value = {
        "decision": "action",
        "action": {
            "tool": "fs.create_note",
            "arguments": {"filename": "note.txt", "text": "hello"},
        },
    }
    value.update(updates)
    return value


def test_valid_proposal_and_explicit_finish(parser):
    parsed = parser.parse(json.dumps(action()))
    assert isinstance(parsed, ActionDecision)
    assert parsed.action.arguments == {"filename": "note.txt", "text": "hello"}
    finish = parser.parse('{"decision":"finish","status":"blocked","reason":"No approved target"}')
    assert isinstance(finish, FinishDecision)
    schema = parser.schema()
    assert (
        schema["oneOf"][0]["properties"]["action"]["oneOf"][0]["properties"]["tool"]["const"]
        == "fs.create_note"
    )


@pytest.mark.parametrize(
    "text",
    [
        '```json\n{"decision":"finish","status":"completed","reason":"ok"}\n```',
        'Here is JSON: {"decision":"finish","status":"completed","reason":"ok"}',
        '{"decision":"finish","status":"completed","reason":"ok"} trailing',
        '{"decision":"finish","decision":"action","status":"completed","reason":"ok"}',
        '{"decision":"finish","status":"completed","reason":NaN}',
        '{"decision":"finish","status":"completed","reason":"ok","code":"print(1)"}',
        '{"decision":"finish","status":"completed","reason":1}',
        '{"decision":"finish","status":"completed","reason":""}',
        "[]",
        "{}",
        "null",
        "[",
        "x" * 65537,
        "[" * 2000 + "]" * 2000,
        'import os; os.system("echo unsafe")',
        "rm -rf sample",
    ],
    ids=lambda text: text[:60] if len(text) <= 100 else f"large-input-{len(text)}",
)
def test_entire_answer_must_be_one_strict_decision(parser, text):
    with pytest.raises(ModelError) as error:
        parser.parse(text)
    assert error.value.error.code == ErrorCode.OUTPUT
    assert str(error.value) == "MODEL_OUTPUT_INVALID"


@pytest.mark.parametrize(
    "change",
    [
        "unknown-tool",
        "bad-type",
        "extra-argument",
        "extra-action",
        "missing-observation",
        "empty-ref",
    ],
)
def test_tool_catalog_and_arguments_are_strict(parser, change):
    value = action()
    proposal = value["action"]
    if change == "unknown-tool":
        proposal["tool"] = "shell.execute"
    elif change == "bad-type":
        proposal["arguments"]["text"] = 1
    elif change == "extra-argument":
        proposal["arguments"]["python"] = "print(1)"
    elif change == "extra-action":
        proposal["script"] = "print(1)"
    elif change == "missing-observation":
        proposal["target_ref"] = "target"
    else:
        proposal.update(target_ref="", observation_id="obs")
    with pytest.raises(ModelError):
        parser.parse(json.dumps(value))


def test_code_is_only_literal_tool_data_never_executed(parser, tmp_path):
    sentinel = tmp_path / "executed"
    text = f"```python\nopen({str(sentinel)!r}, 'w').write('unsafe')\n```"
    value = action()
    value["action"]["arguments"]["text"] = text
    assert parser.parse(json.dumps(value)).action.arguments["text"] == text
    assert not sentinel.exists()


def test_empty_catalog_can_only_finish():
    parser = OutputParser({})
    assert parser.schema()["properties"]["decision"]["const"] == "finish"
    assert isinstance(
        parser.parse('{"decision":"finish","status":"blocked","reason":"No tools"}'), FinishDecision
    )
    with pytest.raises(ModelError):
        parser.parse(json.dumps(action()))


def test_json_float_overflow_rejected():
    from victus.agent.output_parser import strict_json

    with pytest.raises(ValueError):
        strict_json('{"value":1e999}')
