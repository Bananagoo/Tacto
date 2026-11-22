---
paths:
  - "server/tacto/contract.py"
  - "server/tacto/contract_export.py"
  - "contract/**"
---

# Contract rules

- `server/tacto/contract.py` is the source. `contract/` (schemas, examples, the recorded sample) is generated from it: run `make contract` and `make sample` after any change. Tests fail if the committed files are stale.
- **Any change needs the vision owner's sign-off before it is committed**, and the UI team must be told. They build against the schema and the mock.
- One message each way: `State` from the server, `SetVoltage` from the browser. Do not add a message without sign-off.
- Units are in the field comments: amps, volts, hertz, 0..1 positions. Current is signed `a → b`; a battery's `a` is its positive end.
- A piece's id is its segment (`segment_id`). Do not invent other ids.
