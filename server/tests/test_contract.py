from pydantic import TypeAdapter

from tacto.contract import ClientMessage


def test_client_messages_parse():
    adapter = TypeAdapter(ClientMessage)
    assert (
        adapter.validate_json('{"type":"answer","choice":"brighter","via":"voice"}').via == "voice"
    )
    assert adapter.validate_json('{"type":"calibrate_touch","corner":2}').corner == 2
