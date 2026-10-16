# Pilot Frontend Redesign Plan — "Flight Deck"

## 1. Executive Summary & Design Vision
Pilot is an AI project coordinator that couples Telegram check-ins, GitHub automated verification, and a proactive Guide coordinator agent. This redesign replaces the generic appearance with **"Flight Deck"**: an instrument-dense, calm, opinionated operational console. It draws specifically from 5 reference products:

1. **Taiga Scrum**: Top progress bar with status/effort readouts, Sprint burndown chart (ideal vs. actual with slip warning dot), and a dense backlog table with block pill tags and drag handles.
2. **Linear**: Keyboard-first dark aesthetic, collapsible sidebar, docked resizable Guide agent panel with "T-X added to context" chips, and GitHub verification cards styled after Linear PR result cards (`Changed 2 files +22 -10` with commit SHA and confidence verdict). Cmd+K command palette.
3. **Taiga Kanban**: Multi-lane Kanban with swimlanes (grouped by Team Member or Block), WIP limit indicators with striped alert bands, Compact/Expanded view toggle, red-tinted blocked cards, and amber unverified completion edges.
4. **MS Project / Dynamics 365**: Project lifecycle stepper at top (`Planning` → `Assigned` → `Running` → `Verifying` → `Closed`) with KPI health block, plus a dedicated Timeline Gantt page with WBS table, % complete rings, dependency elbow lines, milestone diamonds, and projected slip tails.
5. **Planti**: Soft dashboard widgets (restricted to Overview & My Tasks): pastel tinted KPI tiles, rounded donut card with completion %, grouped today/tomorrow task horizon with avatar stacks, and a deadline calendar countdown.

---

## 2. Reference Mappings (Acceptance Matrix)

| Reference | Target View / Component | Implementation Details |
| :--- | :--- | :--- |
| **1) Taiga Scrum** | `BurndownHeader.jsx`, `Plan.jsx` | Progress bar strip + burndown chart with ideal vs verified effort points, backlog list with drag handles, block tags, owner dots. |
| **2) Linear** | `ProjectShell.jsx`, `GuideDockPanel.jsx`, `CommandPalette.jsx`, `TaskDrawer.jsx` | Dark ops shell, Cmd+K palette, docked Guide agent panel with "T-7 added to context" and GitHub verification card (`Changed 2 files +22 -10`), event timeline. |
| **3) Taiga Kanban** | `Board.jsx` | Swimlanes (grouped by Member or Block), WIP limit headers with red hatched warning stripes, Compact/Expanded zoom switch, red-tinted blocked cards, amber unverified edges. |
| **4) MS Project / Dynamics** | `LifecycleStepper.jsx`, `Timeline.jsx` | 5-stage lifecycle stepper with KPI block; Timeline with WBS table, % complete rings, SVG Gantt bars, dependency lines, milestone diamonds, Today marker, red slip extensions. |
| **5) Planti** | `Overview.jsx` | Pastel tinted stat tiles, large donut card (% complete), today/tomorrow grouped task horizon, deadline calendar card, live countdown timer. |

---

## 3. Design Tokens ("Flight Deck")

### Dark Theme (Default)
- **Background**: `#0A0B0D`
- **Surface**: `#111316`
- **Surface Raised**: `#171A1E`
- **Border**: `#23272D` (hairline 1px)
- **Text Primary**: `#E8E6E1`
- **Text Muted**: `#8A8F98`
- **Accent**: Signal Orange `#FF6B3D` (primary CTAs, today marker, focus ring)

### Light Theme (Warm "Paper" Planti Softness)
- **Background**: `#F5F2EC`
- **Surface**: `#FBFAF7`
- **Surface Raised**: `#EFEBE3`
- **Border**: `#E4DFD5`
- **Text Primary**: `#1B1B18`
- **Text Muted**: `#78756D`
- **Accent**: Signal Orange `#FF6B3D`

### Semantic Status Colors (Dot + Soft Tint)
- `todo`: `#6B7280` (Neutral Grey)
- `in_progress`: `#4C8DFF` (Linear Blue)
- `blocked`: `#F0524A` (Signal Red)
- `claimed_done`: `#F2B33D` (Amber / Unverified)
- `needs_review`: `#A78BFA` (Review Purple)
- `verified_done`: `#3DD68C` (Verified Emerald)

### Member Palette (6 Colorblind-Safe Hues)
1. `#4C8DFF` (Blue - Kabir / Lead)
2. `#3DD68C` (Green - Aarav)
3. `#F2B33D` (Gold - Priya)
4. `#A78BFA` (Purple - Rohan)
5. `#00D2D3` (Cyan - Member 5)
6. `#FF6B8B` (Rose - Member 6)

### Typography
- UI & Body: **Geist Sans** (`@fontsource/geist-sans`)
- IDs, Numerals & Code: **Geist Mono** (`@fontsource/geist-mono`)
- Homepage Headline Accents: **Instrument Serif** italic (`@fontsource/instrument-serif`)

---

## 4. Page Map & Route Architecture
- `/` — **Homepage**: Marketing-quality full bleed hero with Spline 3D paper-plane flight through task nodes (and Canvas/SVG constellation fallback), interactive mini-preview of live board with Telegram chat flip, horizontal 4-step flow, asymmetric bento, demo metrics strip.
- `/p/:code` — **Project Shell**:
  - `overview` (default or tab) — **Executive Overview**: Taiga burndown + Planti dashboard (donut, KPI tiles, today horizon, calendar countdown).
  - `board` — **Taiga Kanban**: Swimlanes, WIP limit warnings, compact/expanded zoom, red blocked cards, amber unverified edges.
  - `plan` — **Taiga Backlog**: Dense WBS list, block tags, load bars per member, oversize warnings, Bundle & Assign modal.
  - `timeline` — **MS Project Timeline**: Interactive Gantt, WBS table, % complete rings, dependency arrows, milestone diamonds, slip extensions.
  - `graph` — **Topological DAG**: React Flow graph with owner colors, glowing red downstream bottleneck slip paths.
  - `contributions` — **Recharts Line Chart & Ledger**: Cumulative commits and lines delivered over time.
  - `activity` — **Linear Audit Feed**: Filterable event ledger.
  - `lead` — **Lead Control Center**: GitHub repo connection, collaborator enrollment (Telegram phone/ID + GitHub), kickoff controls.
- Global Overlays:
  - **Docked Guide Agent Panel**: Floating/dockable Linear-style agent with context chips, streamed thinking, and GitHub verification cards.
  - **Command Palette (`Cmd+K` / `Ctrl+K`)**: Rapid navigation, follow-up execution, task jump.
  - **Task Drawer**: Deep Linear-style task inspector with verification report, criteria checkboxes, and Telegram thread.

---

## 5. Seeded Mock Data Architecture (`/src/mock/snapshot.ts`)
To ensure offline autonomy, the mock snapshot contains:
- 4 real team members (Kabir [Lead], Aarav, Priya, Rohan) with Telegram IDs and GitHub handles.
- 16 engineering tasks across 4 cohesive blocks (Gateway API, Database Schemas, Checkout Flow, Webhook Ledger).
- 2 active blockers with routing paths (T-2 blocked on webhook URL, T-8 blocked on credentials).
- 1 open contradiction with conflicting Telegram statements.
- Commit log with real file diffs and SHA hashes.
- 30 immutable event log records.

---

## 6. Implementation Phases
1. **Phase 1: Foundations & Tokens**: Fonts, Tailwind tokens, CSS variables, theme toggling, `/src/mock/snapshot.ts`.
2. **Phase 2: App Shell, Stepper & Command Palette**: Collapsible sidebar, MS Project lifecycle stepper, docked Guide panel, Cmd+K palette.
3. **Phase 3: Homepage with Spline 3D & Live Preview**: Spline paper plane / constellation scene, interactive board miniature, bento grid.
4. **Phase 4: Overview Page (Planti + Taiga Burndown)**: Progress strip, burndown area chart, Planti donut and KPI tiles, deadline calendar.
5. **Phase 5: Taiga Kanban Board**: Member & Block swimlanes, WIP limits, compact/expanded view modes, red blocked card tints.
6. **Phase 6: Plan & Timeline**: Dense backlog with drag handles, MS Project Gantt chart with dependency lines and slip extensions.
7. **Phase 7: Task Drawer, Graph, Contributions & Activity**: Linear issue inspector, React Flow DAG with slip paths, Recharts lines.
8. **Phase 8: Verification & Visual Polish**: Browser testing at 1440px and 390px, responsive polish, and acceptance checklist audit.
