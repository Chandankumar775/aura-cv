# AURA-CV Design System

Mode: **Operate** (analysts triaging assurance findings). The scene: a secured operations room, low ambient light, long sessions, often projected for a review board. Dark was chosen for that scene, not by category.

## World

- **Ground:** a live three.js terrain (`ui/src/components/TerrainScene.tsx`): a GPU-displaced point field with topographic contour bands and a slow sensor sweep. It is drawn from the subject's world (aerial reconnaissance over terrain), bundled locally, capped at 30 fps and 1.5× pixel ratio, paused in hidden tabs, and reduced to a single static frame under `prefers-reduced-motion`.
- **Glass:** panels are windows onto that ground. `.glass` (content panels), `.glass-strong` (chrome, drawers, palette, toasts) and `.glass-inset` (wells inside a panel). Each has one edge highlight and one offset shadow. The blur is what separates content from the moving terrain, never decoration on a static page.
- **Signature moment:** the dashboard **trust chain** (contributors → dataset → model → inference records → operating batch). Nodes resolve in sequence and connectors draw between them in the colour of the upstream verdict; the overall disposition wipes in once. No other entrance choreography.

## Tokens (`ui/src/index.css`, `@theme`)

| Role | Value |
|---|---|
| canvas | `#080b10` + horizon glow gradients |
| ink / ink-2 / ink-3 | `#e8edf4` / `#a3aebd` / `#6c7787` |
| line / line-soft (translucent) | `#ffffff17` / `#ffffff0c` |
| raised / hover (translucent) | `#ffffff0b` / `#ffffff10` |
| brand (interactive only, never a verdict) | `#8db7ff` |
| accept / review / quarantine / gap | `#3fbf8f` / `#e8ad3d` / `#ef5a5f` / `#8a94a3` |

Verdicts are always **text label + colour**; UNAVAILABLE is grey with a dashed edge.

## Type

IBM Plex Sans (UI) and IBM Plex Mono (digests, ids, measurements only), self-hosted via `@fontsource`. Tabular numerals everywhere. Headings are 28 px, tracking −0.02em, balanced. No eyebrow labels above headings.

## Motion

- Transitions run 150–250 ms on `cubic-bezier(0.16, 1, 0.3, 1)`.
- Panels (drawers, command palette, toasts) enter with blur-to-sharp.
- Only state changes move.

## Components

- `DispositionBadge`, `SeverityBadge`, `ConfidenceMeter`, `DigestText`, `CanvasOverlay`, `VerificationChecklist` and `UnavailableCard` live in `ui/src/components/ui.tsx`.
- The trust chain and the attention queue live in `components/assessment.tsx`.
- `CommandPalette` (Ctrl K or /) and `Toasts` live in `components/CommandPalette.tsx`.
