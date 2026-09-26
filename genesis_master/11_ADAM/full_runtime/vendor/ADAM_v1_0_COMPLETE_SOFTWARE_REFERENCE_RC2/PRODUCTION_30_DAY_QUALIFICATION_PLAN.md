# ADAM v0.43 — 30 Actual Wall-Clock Day Qualification

## Runnable controller

`production_qualification/run_30_day_qualification.py` is resumable and records actual OS wall-clock time. It refuses to issue a production certificate before the configured duration has elapsed. Test clocks are permanently ineligible for production certification.

## Default run

```bash
python production_qualification/run_30_day_qualification.py \
  --root /var/lib/adam-v043/qualification \
  --duration-days 30 \
  --cycle-seconds 60
```

Linux service and Windows launchers are included.

## Workload

The controller alternates governed state reactions, verifies distributed convergence, injects scheduled leader loss and recovery, captures latency and availability, preserves the complete intent history and emits quorum-signed interim and final reports.

## Minimum gates

- at least 30 × 24 elapsed hours;
- no backward-clock event;
- expected minimum cycle count;
- zero integrity failures;
- distributed convergence after every cycle;
- successful failover and recovery events;
- availability at or above the approved SLA;
- p99 latency below the approved target;
- signed daily reports with valid production HSM/KMS quorum;
- restart/replay evidence after host or process interruption;
- final package independently verified.

## Current release evidence

A short real-wall-clock smoke qualification proves that early certification is rejected and that the same controller can issue a certificate only after its configured real duration passes. Thirty days cannot be compressed into this build session; the external run is the evidence required to close the gate.
