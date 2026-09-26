# Windows R4 Production-Soak Correction

**Release:** `0.50.1.dev4`

## Failure corrected

The R3 smoke test assumed nine authority cycles would always complete before a 0.864-second qualification duration. On the target Windows host, real filesystem and cryptographic work exceeded that interval, so the expected pre-duration rejection was no longer valid.

## Runtime correction

A new production soak starts its certified wall-clock interval only after the initial authority cluster has been constructed. Initialization overhead is therefore excluded from a soak that has not begun processing cycles. Existing resumable soak state retains its original certified start time.

## Test correction

The smoke gate now uses two independent controllers:

1. a one-day controller that must reject immediate finalization, independent of machine speed;
2. a short controller that runs one successful cycle, measures the remaining duration, waits for that remainder plus a safety margin, and then must finalize.

No test is skipped or weakened. The duration, minimum-cycle, integrity, availability and latency gates remain active.
