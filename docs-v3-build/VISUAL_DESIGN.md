# Clayfield — Visual Design System

**Design direction:** Industrial CAD foundation with a premium engineering-software finish.  
**Character:** Precise, restrained, technical, calm, and visually polished.  
**Avoid:** Gaming UI, excessive glow, glassmorphism, decorative gradients, oversized pill buttons, and ornamental animation.

## 1. Brand identity

- Wordmark: `CLAYFIELD`, paired with a small technical geometric mark.
- Mark concept: abstract topographic contour, relief cross-section, or computational surface geometry.
- Avoid literal pottery wheels, pots, hands, or clay-tool illustrations.
- The mark must remain legible at application-icon scale and monochrome.
- Primary brand placement: upper-left of the main menu/title region; compact, never a large banner.

## 2. Color tokens

| Token | Hex | Use |
|---|---|---|
| `app.bg` | `#17191D` | Main application background |
| `panel.bg` | `#202329` | Dock panels and panel interiors |
| `surface.raised` | `#272B32` | Inputs, selected cards, raised controls |
| `border.subtle` | `#343941` | Separators, panel edges, control outlines |
| `text.primary` | `#E5E3DD` | Main labels and values |
| `text.secondary` | `#9299A3` | Supporting labels and metadata |
| `accent.primary` | `#62B5C5` | Active state, selection, focus, actionable data |
| `accent.secondary` | `#D49A63` | Secondary emphasis, caution, selected non-primary annotations |
| `state.success` | `#75B89A` | Valid/completed states |
| `state.warning` | `#D49A63` | Warnings and caution |
| `state.error` | `#D87575` | Errors and invalid states |

### Color rules

- Cyan is functional, not decorative. Use it for active selections, keyboard focus, interactive affordances, and important live measurements.
- Copper is secondary. Do not use it for routine selection or every highlighted value.
- Do not communicate analysis severity or mask state by color alone; pair color with labels, patterns, outlines, or numeric values.
- Maintain readable contrast for disabled controls. Disabled must not mean invisible.
- Keep borders low contrast; use spacing and alignment before adding more lines.

## 3. Typography

- Interface family: Inter (or a metrically similar installed sans-serif fallback).
- Technical/numeric family: IBM Plex Mono (or a metrically similar monospace fallback).
- Use sans-serif for navigation, labels, and explanatory text.
- Use monospaced numerals for dimensions, coordinates, mesh counts, thresholds, and parameter values.
- Use restrained hierarchy: page/workspace label, section label, control label, helper text.
- Prefer sentence case for normal labels. Compact uppercase is reserved for small panel/section identifiers where it improves scanning.

Suggested logical sizes:

| Role | Size |
|---|---:|
| Workspace / panel title | 13–14 px, semibold |
| Section label | 11–12 px, medium, optional tracking |
| Control label | 12–13 px |
| Numeric value | 12–13 px, monospace |
| Helper / status text | 11–12 px |
| Main menu | 12–13 px |

## 4. Geometry, spacing, and density

- Overall density: moderate. Favor useful information density with comfortable control spacing.
- Use a consistent 4 px base spacing scale; common gaps are 4, 8, 12, 16, and 24 px.
- Standard control height target: 28–32 logical px; primary action target: 32–36 px.
- Buttons are rectangular with modest corner rounding (approximately 3–5 px), not pill-shaped.
- Inputs and numeric fields align consistently; units should not wrap away from the value.
- Panel headings are minimal, separated by whitespace and thin separators rather than nested card decoration.
- Use cards only when a group needs a distinct surface or state; do not wrap every control in a card.

## 5. Component styling

### Buttons

- Primary: raised surface with cyan emphasis on hover/focus/active; reserve filled cyan for the single dominant action in a context.
- Secondary: neutral raised or outlined control.
- Destructive: restrained error treatment and explicit confirmation only when the action is genuinely destructive.
- Icon-only buttons require tooltips and accessible names.

### Numeric fields and sliders

- Numeric fields are directly editable and use monospaced values.
- Units are always visible (`mm`, `°`, `%`, `px`, triangles), not implied by a tooltip.
- Slider and spin-box values remain synchronized.
- Support fine adjustment and keyboard entry. Do not make a slider the only way to set a precise value.
- Define sensible min/max/step values from the actual processing model during implementation; do not invent unsupported ranges.

### Tabs and navigation

- Workspace tabs are horizontal across the top of the right settings dock.
- Selected tab uses clear text emphasis and a restrained cyan indicator.
- Hover and keyboard-focus states are distinct from selected state.
- Keep labels visible: `SOURCE`, `MODEL`, `SURFACE`, `CLEANUP`, `OUTPUT`.

### Icons

- Use one consistent technical line-icon family.
- Active/selected icons may use a filled state, but do not mix unrelated icon styles.
- Use tooltips and accessible text for ambiguous icons.
- Prefer simple geometric symbols over illustrative clip-art.

## 6. Viewport visual treatment

- Default viewport background: dark graphite.
- Offer a small curated set of alternate professional backgrounds; do not expose an unrestricted color picker in the first release.
- Default model material: matte technical gray, optimized to reveal geometry.
- Optional materials: neutral ceramic/clay and ivory/white variants.
- Default lighting: one directional light with soft shadows. Expose a small number of practical controls for direction and intensity; avoid a complex lighting rig.
- Ground grid and ground shadow are independently configurable.
- Grid is subtle and scale-aware; it must not compete with the model.
- The default camera is a three-quarter view that reveals relief depth. Frame the object on generation, then preserve the user's camera position during ordinary workspace changes.
- Provide a compact clickable XYZ axis gizmo. Clicking an axis aligns the camera; do not add a large orientation cube in the initial design.

## 7. Analysis and mask visualization

### Analysis

- Support two display modes: heatmap replaces the clay material, or translucent heatmap overlays the clay material.
- Heatmap severity uses a restrained sequential progression (neutral → yellow → orange → red) and includes a legend and numeric range where meaningful.
- Never imply a universal severity scale if the selected analysis method has a different measurement basis. Label the metric and units.
- Provide a non-color cue (contour, hatch, label, or threshold outline) for important classifications.

### Mask

- Eligible/selected region: cyan.
- Protected region: dark gray.
- Provide opacity control and independent show/hide.
- Hiding the overlay must not disable or clear the mask.
- Show a legend whenever the overlay is visible.
- Mask preview is non-destructive; generating or editing a mask does not alter geometry.

## 8. Brush cursor and floating palette

- Normal brush cursor: circular outline with a readable falloff indication.
- Advanced brush cursor: add center point and strength indicator.
- Cursor size reflects the physical brush radius projected into the viewport.
- Brush cursor must remain visible over both light and dark model areas; use a subtle contrasting outline rather than a large glow.
- Contextual floating palette appears when a viewport tool is active. It can be moved and pinned; when not pinned it should stay out of the way.
- Floating palette contains only essential immediate controls. Full parameter controls remain in the right-side CLEANUP panel.
- Palette must avoid covering the cursor/target area; reposition when necessary or allow the user to move it.

## 9. Motion and feedback

- Workspace changes may use a subtle, short fade or crossfade. No elaborate sliding panels.
- Preserve each workspace's scroll position, selections, and control values when switching tabs.
- Do not animate numerical values in a way that makes precise reading difficult.
- Use status-bar progress for ordinary operations. Keep the interface responsive and expose cancellation when the underlying operation can be safely cancelled.
- Errors and warnings should be actionable and specific. Avoid modal dialogs for routine status messages.

## 10. Accessibility and display scaling

- Treat specified sizes as logical pixels and support high-DPI scaling.
- Keyboard focus must be visible.
- Do not rely on color alone for selection, severity, or validation.
- Keep disabled text readable.
- Tooltips supplement, but do not replace, labels or units.
- Test at the default window size and at smaller supported dimensions before release.
