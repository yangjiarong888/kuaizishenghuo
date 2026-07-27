# Mall Order Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task.

**Goal:** Remove hard-coded personal test data, require an explicit address-mutation capability, and extract pure order value types from the 3097-line mall script while preserving safe checkout behavior.

**Architecture:** CLI validation runs before Driver creation. Personal test data comes only from explicit arguments or environment variables. Pure parsing and snapshot types move to `flows/mall_order_types.py`; `scripts/run_mall_order_flow.py` re-exports them for compatibility.

## Constraints

- Default flow must not submit an order or mutate an address.
- Address creation, editing, copying, or forced selection requires both the existing action flag and `--allow-address-mutation`.
- No fixed phone, name, WeChat ID, or street address may remain in source defaults.
- All changes use RED→GREEN tests and full offline regression.

### Task 1: Safe CLI Validation

**Files:** `testcases/test_mall_order_cli.py`, `scripts/run_mall_order_flow.py`.

- [ ] Add tests for empty personal-data defaults, default `submit_order=False`, rejection of mutation flags without capability, acceptance with capability, and validation before Driver creation.
- [ ] Verify RED.
- [ ] Add `--allow-address-mutation`, `validate_args(args)`, `main(argv=None)`, and environment-backed empty personal-data defaults.
- [ ] Return exit code `2` for invalid CLI safety combinations without logging raw values.
- [ ] Run focused and full offline tests.

### Task 2: Pure Mall Order Types

**Files:** `flows/mall_order_types.py`, `testcases/test_mall_order_types.py`, `scripts/run_mall_order_flow.py`.

- [ ] Add failing tests for peso parsing, formatting variants, invalid input, and numeric tolerance.
- [ ] Extract `ProductSnapshot`, `AmountSnapshot`, `SubmitResult`, `parse_money`, and `nearly_equal` without Appium dependencies.
- [ ] Re-export imported names from the original script.
- [ ] Run focused and full offline tests.

### Task 3: Verification and Report

**Files:** `docs/reviews/2026-07-22-mall-order-boundary-review.md`.

- [ ] Compile all sources in memory.
- [ ] Run all offline tests with zero failures.
- [ ] Scan for fixed personal defaults and sensitive values.
- [ ] Record line-count reduction and remaining MallOrderFlow decomposition risks.
