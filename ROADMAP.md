# Draft Roadmap — neewer-ble-homeassistant

No `ROADMAP.md`, `docs/` strategy content, or companion `/context` repository exists in this
repository. This document is inferred from the README, `CLAUDE.md`, commit history, git tags,
and the current code (`const.py`, `neewer_device.py`, tests). Anything not directly stated by
the maintainer is marked **(guess)**.

## Purpose

A Home Assistant custom integration (HACS) that controls Neewer LED lights over Bluetooth Low
Energy, without depending on the lights' Wi-Fi connectivity. It reimplements the reverse-engineered
Neewer BLE protocol (credited to the NeewerLite and NeewerLite-Python projects) as a native HA
`LightEntity`, supporting brightness, color temperature, and RGB (HSI) control across two protocol
generations ("standard" and "Infinity").

## Current state

- Version `0.4.0-beta.3`, tagged betas from `v0.3.0` → `v0.4.0-beta.3`; no stable `v0.4.0` release yet.
- CI is green across the board: unit tests, Hassfest validation, and HACS validation all pass on
  `main` and the latest beta tag.
- Two hardware models are confirmed **Tested**: GL1 Pro and PL60C. The rest of `SUPPORTED_MODELS`
  (in `const.py`) — MS60C, RGB660/660 PRO, RGB480/530, SL-80, SNL-660, GL1, CB100C/CB300B, RGB1,
  TL60 RGB, MS150B, AP150C, RGB168, and several others — are either "Should Work (Untested)" or
  explicitly "Beta - Community Testing Needed".
- Recent merged work (#1, #2) hardened Bluetooth connection handling, added a Home Assistant test
  suite (`tests/`), and applied hardware feedback for PL60C and AP150C profiles.
- The project has a structured contribution path for hardware feedback: `device_support.yml` and
  `bug_report.yml` issue forms explicitly ask reporters for the exact BLE advertised name and which
  controls were verified. This suggests the maintainer's main current bottleneck is **hardware
  confirmation from real owners**, not code development velocity.
- Known, documented limitations (from README "Known Limitations"): no state feedback from the light
  when changed via the Neewer app (optimistic state only), single-controller BLE limitation, and no
  Wi-Fi support by design.

## Goals

### Next

- Reach a stable `v0.4.0` release once enough of the beta model list (MS150B, AP150C, RGB168) has
  community hardware confirmation, or ship with clearer beta labeling if confirmation stalls.
- Continue converting "Should Work (Untested)" / "Beta" entries in `SUPPORTED_MODELS` to "Tested" as
  device-support issues come in, following the existing `device_support.yml` triage flow.
- Keep CI (tests, Hassfest, HACS validation) green as new device profiles and protocol variants are
  added — this is the main regression guard given there's no way to test against real hardware in CI.

### Later

- Broader protocol coverage for additional Neewer product lines as they're released, mirroring
  upstream NeewerLite-Python protocol updates.
- Possible HACS default-repository submission once out of beta (currently installed via custom
  repository only).
- Nothing else much, just as stable as realistically possible Neewer support in HomeAssistant

## Non-goals

- Wi-Fi-based control of Neewer lights (explicitly out of scope per README "Known Limitations").
- Acting as a general BLE library — this integration is scoped to Home Assistant and Neewer's
  specific GATT protocol.
- Guaranteeing multi-controller support (Neewer app + Home Assistant simultaneously) — a hardware/
  protocol limitation, not something the integration can fix.

## Open questions for Paul

1. Is there an actual roadmap, milestone list, or private notes (e.g., in GitHub Projects, a wiki,
   or a `/context` repo not present in this environment) that should supersede this draft?
2. What's the bar for promoting a model from "Beta" / "Should Work (Untested)" to "Tested" — one
   confirmation via `device_support.yml`, or more than one independent report?
3. Is a stable `v0.4.0` release blocked purely on hardware confirmations, or are there known
   code-level gaps (e.g., specific models with reported protocol issues) not yet visible in open
   issues?
4. Is improving real-time state feedback (vs. optimistic/assumed state) an actual priority, or is
   the current "assumed_state" model an accepted permanent design choice for this protocol?
5. Any plans to pursue HACS default-repository listing, or is custom-repository installation the
   intended long-term distribution method?
</content>
