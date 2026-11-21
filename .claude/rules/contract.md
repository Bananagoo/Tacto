---
paths:
  - "server/tacto/contract.py"
  - "web/src/contract.ts"
---

# Contract rules

- `server/tacto/contract.py` is the source of truth. `web/src/contract.ts` mirrors it field for field. Edit both in the same commit.
- Additive changes only: new optional fields with defaults. Renaming or removing a field needs the team's agreement first, because three other sessions are building against it.
- Field names are snake_case on both sides (the JSON is passed through untouched).
- Units go in the name when a number could be misread: `pulse_hz`, `source_voltage`.
- After any change run `make check`; `server/tests/test_contract.py` must still pass, and make sure `server/tests/test_session.py` exercises the new field.
- Note the change in one line at the top of your commit message: `contract: add Probe.short`.
