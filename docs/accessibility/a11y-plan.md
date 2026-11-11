# Accessibility plan

Target: **WCAG 2.2 AA** for the planned web app. Personal project, but a canvas
app is easy to make unusable with a keyboard or screen reader; these basics are
cheap and worth doing.

## Canvas / viewport

- Provide keyboard camera controls (orbit, pan, zoom, fit) and document them.
- Expose model facts as text: dimensions, height range, triangle count,
  warnings. Screen readers cannot read the canvas.
- Announce status/progress via ARIA live regions (polite for progress, assertive
  for errors).
- Ensure the brush is not the only way to accomplish a task; provide numeric
  inputs for all brush settings.

## Keyboard

- All controls reachable and operable by keyboard.
- Visible focus indicators; logical focus order.
- Floating source card: keyboard move/resize or numeric position/size fields.
- Resizable panels: keyboard-resizable separators.
- Dialogs: focus trap, Escape to close, return focus to trigger.
- Shortcuts documented in-app; avoid single-key shortcuts that conflict with
  assistive tech.

## Visual

- Colour contrast ≥ 4.5:1 for text, ≥ 3:1 for UI.
- Do not encode height only by colour; offer numeric readouts and patterns.
- Respect `prefers-reduced-motion` (camera animation, transitions).
- Support light/dark themes with accessible palettes.

## Forms

- Every input has a label; errors are programmatically associated.
- `ParameterRow` exposes slider + numeric + reset with accessible names.

## Testing

- `eslint-plugin-jsx-a11y`, axe in component and E2E tests.
- Minimum success criteria to verify: 1.4.3 contrast, 2.1.1 keyboard, 2.2.1
  timing adjustable, 2.4.3 focus order, 2.4.7 focus visible, 2.5.7 dragging
  movements, 4.1.2 name/role/value. Canvas: text alternative + live regions.
- Manual screen-reader matrix (NVDA/JAWS on Windows, VoiceOver on macOS/iOS).
- Keyboard-only pass for each milestone exit.

## Legal note

WCAG 2.2 AA is a reasonable baseline for ADA/EAA expectations. Since this is a
personal project, treat it as a quality goal, not a compliance program.

---

Part of the web build docs. Index: [docs/README.md](../README.md).
