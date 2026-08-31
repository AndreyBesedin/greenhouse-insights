# Greenhouse Intelligence Platform — UI / UX & Frontend Design Brief

## 1. Purpose of This Document

This document is intended to be used as a product and design prompt for tools such as Lovable, Claude Design, or a frontend coding agent.

The goal is to design and scaffold the first polished user interface for a greenhouse intelligence platform.

The frontend should be implemented in:

- React
- TypeScript

The design should be built around reusable shared components and a coherent design system from the beginning.

This is not a one-off mockup. The interface should look like the beginning of a real product that could later support multiple clients, sites, greenhouses, crops, operators, and data sources.

The visual language should feel:

- modern
- calm
- trustworthy
- agricultural without being rustic
- friendly without being childish
- data-rich without looking like a generic enterprise BI dashboard
- operational rather than scientific
- suitable for daily use by growers, greenhouse managers, agronomists, and operators

The interface should make the greenhouse feel like a living system rather than a collection of database records.

---

# 2. Product Vision

The platform provides a longitudinal operational view of one or more greenhouses.

It combines greenhouse-level data, plant-level observations, historical state, actions, production information, alerts, and recommendations.

The platform should help users answer questions such as:

- What is happening in my greenhouse today?
- Which plants or zones require attention?
- How much fruit is ready to harvest?
- What changed since yesterday?
- Which plants are under stress?
- What work should my team prioritize?
- What was the state of the greenhouse three days ago?
- How much has been harvested so far?
- Which plants are developing normally?
- Which observations or events explain a change in state?

The first implementation operates on simulated greenhouses, but the interface must not feel like a simulation toy.

A simulated greenhouse should be presented through the same product model that a real greenhouse would eventually use.

Simulation-specific controls should only appear when the selected greenhouse is a simulation.

---

# 3. Product Hierarchy

The initial hierarchy is:

```text
Client / Account
    ↓
Greenhouses
    ↓
Greenhouse
    ↓
Plants
```

The architecture should leave room for a future hierarchy such as:

```text
Organisation
    ↓
Site
    ↓
Greenhouse
    ↓
Zone / Row / Tray
    ↓
Plant
```

The initial UI does not need to expose all future hierarchy levels.

However, components and navigation should not assume that one client can only have one greenhouse.

---

# 4. Authentication and Client Access

The platform should begin with a proper authentication flow.

For the first design, create:

- Login screen
- Logged-in application shell
- User/account menu
- Logout action

The authentication backend does not need to be fully implemented in the first visual prototype if the design tool does not support it.

It is acceptable to mock authentication while maintaining a realistic product flow.

## Login Screen

The login screen should feel polished and simple.

Recommended content:

- product logo / wordmark
- short product description
- email field
- password field
- primary `Sign in` button
- optional `Forgot password?`
- optional future SSO placeholder

Avoid oversized marketing illustrations.

A subtle greenhouse or crop-related visual treatment is acceptable, but keep the interface professional.

Example copy:

> Greenhouse intelligence, from plant to production.

---

# 5. Main Application Shell

After login, the user enters the main application.

The application shell should be reusable across screens.

Recommended structure:

```text
┌──────────────────────────────────────────────────────────────┐
│ Logo / Product   Main navigation               User / Account│
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                      Page content                            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

Possible top-level navigation:

- Greenhouses
- Activity
- Insights
- Settings

Only `Greenhouses` needs to be fully implemented initially.

Avoid building empty navigation sections just for visual completeness.

---

# 6. Greenhouse Landing Page

After login, the default landing page should be the greenhouse list.

The page should immediately answer:

> Which greenhouse do I want to inspect?

## Page Header

Example:

```text
Greenhouses
Monitor your growing environments and daily operations.
```

Include:

- greenhouse count
- optional client/site selector in the future
- compact filter or search if useful

For the first version, keep controls minimal.

---

# 7. Greenhouse Cards

Each greenhouse should be represented by a polished reusable card.

Example information:

```text
Simulation Greenhouse 001

Cherry tomatoes
40 plants
4 rows

Current state
Day 28 of 28

34 Healthy
4 Monitor
2 Action required

3.8 kg ready to harvest

Simulation completed

[Open greenhouse]
```

A second greenhouse might be:

```text
Longitudinal Plant Demo

Cherry tomato
1 plant

Day 0 of 40

Simulation not started

[Open greenhouse]
```

A future real greenhouse might appear as:

```text
Greenhouse North

Vine tomatoes
2,400 plants

Live
Last update 2 min ago

8 plants require attention
```

The card component should therefore support:

- crop
- greenhouse status
- source type: simulation / live
- plant count
- current timestamp/day
- operational summary
- CTA
- optional crop icon or illustration

---

# 8. Crop Identity and Icon System

The platform should visually communicate what is being grown.

Avoid generic colored circles everywhere.

Create or define a reusable crop icon system.

Examples:

- vine tomato
- cherry tomato
- cucumber
- pepper
- strawberry
- lettuce

For the POC, tomato is the only required crop.

A tomato plant in the greenhouse map should be visually recognizable as a tomato plant, even if represented very simply.

Recommended approach:

- build a small SVG icon set
- keep icons stylistically consistent
- prefer clean custom vector icons over random emoji
- store icons centrally
- expose them through a reusable `CropIcon` component

Example API:

```tsx
<CropIcon crop="vine-tomato" size="md" />
```

Possible crop type model:

```ts
type CropType =
  | "vine-tomato"
  | "cherry-tomato"
  | "cucumber"
  | "pepper"
  | "lettuce";
```

The interface should remain elegant even when icons are repeated dozens of times.

For plant map usage, consider a simplified plant symbol:

- small leafy stem
- tomato cluster accent
- crop-specific silhouette

Do not use detailed photorealistic images for every plant.

---

# 9. Design System

Build a small but intentional design system before creating screen-specific styling.

At minimum define:

## Foundations

- typography
- spacing scale
- border radii
- shadows
- semantic colors
- background surfaces
- icon sizing
- motion timing
- breakpoints

## Shared Components

- Button
- IconButton
- Card
- Badge
- StatusBadge
- MetricCard
- Select
- Input
- Tooltip
- Dropdown
- Tabs
- Drawer / SidePanel
- Modal
- ProgressBar
- Timeline
- EmptyState
- LoadingState
- ErrorState
- CropIcon
- PlantIcon
- GreenhouseCard

Avoid styling individual pages independently.

---

# 10. Visual Direction

The platform should feel close to a high-quality modern SaaS product, but with subtle agricultural identity.

Avoid:

- dark industrial control-room aesthetic
- neon colors
- cyberpunk styling
- excessive glassmorphism
- overly rounded toy-like components
- giant gradients
- generic startup purple
- dense enterprise tables as the primary UI
- cartoon farm illustrations
- excessive green everywhere

Prefer:

- warm neutral backgrounds
- restrained green as a semantic/product accent
- natural but muted secondary tones
- strong typography
- generous spacing
- clear visual hierarchy
- soft borders
- limited shadows
- well-designed icons
- readable charts
- subtle motion

The UI should look pleasant enough that a greenhouse operator would willingly keep it open all day.

---

# 11. Semantic Status System

Plant status must have a consistent visual language.

Initial states:

```ts
type PlantOperationalStatus =
  | "healthy"
  | "monitor"
  | "action-required"
  | "unknown";
```

Suggested semantics:

- Healthy: calm positive treatment
- Monitor: warning / amber treatment
- Action required: strong attention treatment
- Unknown: neutral / muted treatment

Do not encode status only using color.

Combine:

- color
- icon or symbol
- label
- tooltip when useful

This is important for accessibility.

---

# 12. Greenhouse Detail Page

The greenhouse detail page is the core product screen.

It should feel like an operational cockpit, but clean and approachable.

Recommended structure:

```text
┌──────────────────────────────────────────────────────────────────┐
│ ← Greenhouses                                                   │
│                                                                  │
│ Simulation Greenhouse 001                    Simulation complete │
│ Cherry tomatoes · 40 plants                                     │
│                                                                  │
│ Day 28 of 28       [timeline / history control]                  │
├──────────────────────────────────────────────────────────────────┤
│ KPI summary                                                      │
├───────────────────────────────────────┬──────────────────────────┤
│                                       │                          │
│        GREENHOUSE PLAN                │      PLANT DETAILS       │
│                                       │                          │
│                                       │                          │
├───────────────────────────────────────┴──────────────────────────┤
│ Priority work / insights                                        │
└──────────────────────────────────────────────────────────────────┘
```

The interface should work both with and without a plant selected.

---

# 13. Greenhouse Header

The greenhouse header should contain:

- back navigation
- greenhouse name
- crop
- greenhouse metadata
- source type
- simulation or live status
- selected/current day or date
- simulation progress if applicable

Example:

```text
Simulation Greenhouse 001

Cherry tomatoes
40 plants · 4 rows

Simulation
Day 14 / 28
Running
```

For a real greenhouse:

```text
Greenhouse North

Vine tomatoes
2,400 plants

Live
Updated 2 minutes ago
```

---

# 14. Simulation Controls

Simulation controls are displayed only for simulated greenhouses.

## Not Started

Display:

```text
Day 0 / 28

[Run simulation]
```

The greenhouse map can already be visible with initial plant positions.

## Running

Display:

```text
Running simulation

Day 12 / 28

████████████░░░░░░░░░

[Pause]   optional
```

The simulation should advance visibly.

The UI should update approximately once per simulated day.

The default presentation speed may be around:

```text
1 simulated day / second
```

This should be configurable in the implementation.

## Completed

Display:

```text
Simulation completed
Day 28 / 28
```

No persistent giant completion banner is necessary.

Historical navigation becomes the primary control.

---

# 15. Progressive Simulation Experience

The simulation should feel alive.

As simulation steps arrive:

- plant visual states update
- KPI values update
- fruit counts change
- harvest totals increase
- alerts appear or disappear
- recommendations change
- selected plant details update
- simulation progress advances

Transitions should be subtle.

Avoid excessive animation.

Recommended motion:

- short cross-fade for numeric values
- subtle status transition
- progress animation
- small highlight when a plant enters `action-required`

The product should communicate change without becoming distracting.

---

# 16. KPI Area

The top of the greenhouse screen should contain a concise operational summary.

Possible cards:

```text
40
Plants

34
Healthy

4
Monitor

2
Need action

3.8 kg
Ready to harvest

18.2 kg
Harvested total
```

Do not create twelve KPI cards.

Four to six is enough.

The hierarchy should make the most operationally important values prominent.

---

# 17. Greenhouse Plan

The greenhouse plan is the central visual element.

Represent the greenhouse as a simplified top-down schematic.

For the primary POC:

```text
4 rows × 10 plants
```

Example:

```text
Row 1
🌿 🌿 🌿 🌿 🌿 🌿 🌿 🌿 🌿 🌿

Row 2
🌿 🌿 🌿 🌿 🌿 🌿 🌿 🌿 🌿 🌿

Row 3
🌿 🌿 🌿 🌿 🌿 🌿 🌿 🌿 🌿 🌿

Row 4
🌿 🌿 🌿 🌿 🌿 🌿 🌿 🌿 🌿 🌿
```

Do not literally use emoji in the final design.

Use a proper reusable vector plant/crop icon.

The map should visually communicate:

- rows
- paths / spacing
- plant identity
- current plant status
- selected plant
- hover state

Potentially include:

- row labels
- greenhouse orientation
- simple tray/bed backgrounds
- subtle structural outlines

Avoid turning this into CAD or 3D visualization.

---

# 18. Plant Representation

Each plant should be clickable.

A plant component might expose:

```tsx
<PlantMarker
  plant={plant}
  crop="vine-tomato"
  status="monitor"
  selected={true}
/>
```

The plant marker should combine crop identity with operational status.

Possible design:

- crop icon in the center
- subtle status ring around it
- small alert indicator when necessary
- selected halo / outline

Example concept:

```text
     status ring
        ↓
    ┌───────┐
    │  🍅   │   ← custom tomato plant icon
    └───────┘
```

The crop identity should remain visible even when status changes.

Do not replace the plant icon entirely with a red/yellow/green traffic-light dot.

---

# 19. Plant Hover State

Hovering a plant should show a compact tooltip.

Example:

```text
Plant 17

Healthy
12 ripe fruits
620 g ready
Last action: Harvest · yesterday
```

Do not overload the tooltip.

Clicking opens the full detail view.

---

# 20. Plant Detail Panel

Selecting a plant should open a persistent side panel or inspector.

Recommended content hierarchy:

## Header

```text
Plant 17
Cherry tomato
Row 2 · Position 7
```

## Current state

```text
Healthy
Fruiting

47 visible fruits
12 ripe
620 g ripe mass
```

## Water / environment

```text
Soil moisture     43%
Temperature       27.1°C
Humidity          69%
```

## Production

```text
Harvested total   2.8 kg
Last harvest      780 g · yesterday
```

## Active insight

```text
Harvest recommended within 1–2 days
```

## History

Display recent events and observations.

## Charts

Show only the most relevant time series.

---

# 21. Plant Data Structure View

Because this POC is also intended to demonstrate the reconstructed structured state, the plant panel should optionally expose the underlying structured data.

Possible UI:

```text
Overview | History | Raw state
```

`Raw state` could display a nicely formatted JSON-like representation.

Example:

```json
{
  "health": "healthy",
  "development_stage": "fruiting",
  "visible_fruit_count": 47,
  "ripe_fruit_count": 12,
  "estimated_ripe_mass_g": 620,
  "soil_moisture_pct": 43
}
```

This should look intentional and useful, not like a developer console pasted into the product.

---

# 22. Timeline / History Navigation

History navigation is a core feature.

After a simulation has completed, the user should be able to navigate all persisted days.

Recommended component:

```text
←   Day 12   ─────────────●─────────────   Day 28   →
```

Or a compact slider/timeline combined with day navigation.

Required actions:

- previous day
- next day
- select day
- return to current day

Example historical-state banner:

```text
Viewing Day 14
Current state is Day 28

[Return to current]
```

This component should later work equally well with real dates for live greenhouses.

---

# 23. Historical State Consistency

When the selected historical day changes, all screen data should update to that point in time:

- KPIs
- plant statuses
- selected plant
- fruit counts
- cumulative harvest
- latest event
- recommendations
- charts
- priority list

The user should feel that they are viewing a snapshot of the entire greenhouse at that historical point.

---

# 24. Plant History Timeline

Within the plant detail panel, display a chronological event stream.

Example:

```text
Day 18
Watered · 700 ml

Day 20
9 ripe fruits detected

Day 21
Harvest recommended

Day 22
Probable harvest · 820 g
Inferred · 94% confidence

Day 23
Normal development resumed
```

Different event origins should be visually distinguishable:

- observed
- human-reported
- automated
- inferred

Keep the visual treatment subtle.

---

# 25. Charts

Use lightweight charts.

Recommended first charts:

- soil moisture over time
- greenhouse temperature
- fruit count by ripeness stage
- estimated ripe mass
- harvest over time
- health / wilting score

Charts should:

- use the same design tokens as the rest of the application
- have good tooltips
- remain readable at small sizes
- avoid unnecessary legends
- avoid 3D
- avoid decorative chart junk

---

# 26. Operational Priorities

Include a section for current recommendations / work priorities.

Example:

```text
Today

High
Plant 31
Inspect possible water stress

Medium
Plant 17
Harvest approximately 1.1 kg

Medium
Plant 24
Check anomalous moisture reading
```

Eventually this can become a proper workload view.

For the POC, a compact list is sufficient.

---

# 27. Empty and Initial States

Design these intentionally.

## No Greenhouses

```text
No greenhouses available
```

## Simulation Not Started

The greenhouse layout should still be visible.

Include a clear primary action:

```text
Run simulation
```

## No Plant Selected

Plant detail panel may show:

```text
Select a plant to inspect its current state and history.
```

## No Alerts

```text
Everything looks healthy.
No active recommendations.
```

Avoid blank spaces that look broken.

---

# 28. Loading States

Use skeletons or restrained loading indicators.

Examples:

- greenhouse list loading
- dashboard snapshot loading
- plant inspector loading
- history loading

Avoid full-screen spinners for small data updates.

---

# 29. Error States

Create reusable errors for:

- failed greenhouse load
- failed simulation start
- failed simulation update
- unavailable historical state

Errors should be readable and actionable.

Example:

```text
Could not load this greenhouse.
Try again.
```

---

# 30. Responsive Behaviour

Primary target:

- desktop
- laptop

The dashboard is information-dense and does not need to be mobile-first.

Still ensure:

- greenhouse list works on tablet/mobile
- navigation remains usable
- greenhouse detail degrades reasonably
- plant detail can become a drawer on narrower screens

Possible desktop layout:

```text
Greenhouse map 65%
Plant inspector 35%
```

On smaller screens:

```text
Greenhouse map
↓
Plant inspector drawer
```

---

# 31. Accessibility

Minimum expectations:

- keyboard-accessible interactive elements
- visible focus states
- sufficient contrast
- plant status not encoded by color alone
- tooltips accessible through focus
- proper semantic button elements
- appropriate ARIA labels for icon-only buttons
- readable typography

---

# 32. Frontend Technical Structure

Use React + TypeScript.

Prefer feature-oriented modules combined with shared design-system components.

Example:

```text
src/
  app/
    router/
    providers/

  design-system/
    components/
    tokens/
    icons/

  features/
    auth/
    greenhouse-list/
    greenhouse-dashboard/
    simulation/
    plant-inspector/
    timeline/
    recommendations/

  domain/
    greenhouse/
    plant/
    observation/
    event/

  api/
    client/
    greenhouse/
    simulation/

  pages/
    login/
    greenhouses/
    greenhouse/

  assets/
    crop-icons/
```

Exact structure may change, but keep:

- design-system components shared
- domain types centralized
- API access separated from components
- crop icons centralized
- page components thin

---

# 33. React Component Ideas

Potential shared components:

```text
AppShell
PageHeader
GreenhouseCard
GreenhouseSelector
GreenhouseStatusBadge
SimulationProgress
SimulationControls
MetricCard
MetricGrid
GreenhouseMap
GreenhouseRow
PlantMarker
PlantTooltip
PlantInspector
PlantSummary
PlantMetrics
PlantEventTimeline
PlantCharts
HistoryNavigator
CurrentStateIndicator
RecommendationList
RecommendationCard
CropIcon
StatusBadge
```

Do not create abstractions prematurely.

Prefer shared components only where repeated patterns actually exist.

---

# 34. Domain Types

Use explicit domain types.

Example:

```ts
type GreenhouseSource = "simulation" | "live";

type SimulationStatus =
  | "not-started"
  | "running"
  | "completed"
  | "failed";

interface GreenhouseSummary {
  id: string;
  name: string;
  crop: CropType;
  source: GreenhouseSource;
  plantCount: number;
  currentDay?: number;
  totalDays?: number;
  simulationStatus?: SimulationStatus;
}

interface PlantPosition {
  row: number;
  positionInRow: number;
  x?: number;
  y?: number;
}

interface PlantState {
  plantId: string;
  status: PlantOperationalStatus;
  developmentStage: string;
  visibleFruitCount: number;
  ripeFruitCount: number;
  estimatedRipeMassG: number;
  harvestedTotalG: number;
  soilMoisturePct: number;
  latestEvent?: PlantEvent;
}
```

Do not let frontend screens invent duplicate versions of the same domain object.

---

# 35. Data Layer

Design the frontend as if it consumes a real API.

Do not deeply couple UI state to local mock arrays.

Potential API:

```text
GET /greenhouses

GET /greenhouses/:greenhouseId

GET /greenhouses/:greenhouseId/state

GET /greenhouses/:greenhouseId/state?day=14

GET /greenhouses/:greenhouseId/timeline

GET /greenhouses/:greenhouseId/plants/:plantId

GET /greenhouses/:greenhouseId/plants/:plantId/history

POST /simulations/:simulationId/run

GET /simulations/:simulationId/status
```

For the first UI prototype, mocked API functions or fixtures are acceptable.

Keep a clean seam so they can later be replaced with the real backend.

---

# 36. Application State

Avoid one giant global state store.

Separate:

- authenticated user state
- current greenhouse
- current historical day
- selected plant
- simulation progress
- remote server state

Use a server-state library if useful, but do not add complexity solely for architecture.

The selected plant and selected day should be reflected consistently across the interface.

---

# 37. Icon Organization

All product icons should come from a consistent source.

Suggested organization:

```text
design-system/
  icons/
    common/
    crops/
    status/
    actions/
```

Examples:

```text
common/
  chevron-left
  calendar
  user
  settings
  refresh

crops/
  vine-tomato
  cherry-tomato
  cucumber
  pepper

status/
  healthy
  monitor
  action-required
  unknown

actions/
  watering
  harvest
  inspection
  pruning
  fertilisation
```

Use one icon style.

Avoid mixing emoji, filled icons, thin-line icons, and custom illustrations randomly.

---

# 38. Crop Icon Behaviour

Crop icons should support:

```tsx
<CropIcon
  crop="vine-tomato"
  size="sm"
/>
```

and:

```tsx
<PlantMarker
  crop="vine-tomato"
  status="action-required"
/>
```

The crop icon represents **what the plant is**.

The status treatment represents **what operational condition it is in**.

Keep those semantics separate.

---

# 39. Design Tokens

Define centralized tokens.

Example categories:

```text
colors
typography
spacing
radius
shadow
motion
z-index
```

Semantic colors should include concepts such as:

```text
background
surface
surface-muted
border
text-primary
text-secondary

brand

status-healthy
status-monitor
status-action
status-unknown

data-temperature
data-moisture
data-harvest
```

Do not scatter arbitrary hex codes throughout components.

---

# 40. Typography

Use a clean sans-serif suitable for operational software.

Hierarchy should include:

- display / page title
- section heading
- card title
- body
- small / metadata
- metric number

Metrics should be visually strong without becoming huge marketing typography.

---

# 41. Visual Tone of the Greenhouse Map

The greenhouse map should be the signature product element.

It should feel more charming and recognizable than a grid of circles.

Possible direction:

- soft greenhouse bed/tray shapes
- subtle paths between rows
- small crop-specific plant icons
- plant icons placed with comfortable whitespace
- row labels
- status rings
- selected state
- hover information

Potential visual metaphor:

```text
┌───────────────────────────────────────┐
│ Row A                                 │
│  🌱  🌱  🌱  🌱  🌱  🌱  🌱  🌱     │
│                                       │
│ Row B                                 │
│  🌱  🌱  🌱  🌱  🌱  🌱  🌱  🌱     │
│                                       │
└───────────────────────────────────────┘
```

Again, replace emoji with custom vector crop icons.

The product should make someone immediately think:

> These are plants in a greenhouse.

not:

> These are nodes in a graph.

---

# 42. Interaction Details

Useful micro-interactions:

- hover plant → tooltip
- click plant → inspector
- click another plant → inspector updates
- click same plant again → optional deselect
- simulation step → subtle value transitions
- historical day change → dashboard snapshot transitions
- status change → subtle visual emphasis
- recommendation click → select corresponding plant
- crop icon hover on greenhouse card → no unnecessary animation

Keep interactions predictable.

---

# 43. Route Structure

Example:

```text
/login

/greenhouses

/greenhouses/:greenhouseId
```

Potential future routes:

```text
/activity
/insights
/settings
```

For historical day selection, either use:

```text
/greenhouses/:greenhouseId?day=14
```

or application state.

Using a query parameter is attractive because historical views become linkable.

---

# 44. Demo Data

Design against at least two greenhouses.

## Simulation Greenhouse 001

```text
Crop: cherry / vine tomato
Plants: 40
Layout: 4 × 10
Duration: 28 days
Status: not-started or completed depending fixture
```

## Longitudinal Plant Demo

```text
Crop: vine tomato
Plants: 1
Duration: 40 days
```

Populate realistic values so the interface does not look like a wireframe.

---

# 45. First Screen Set to Produce

The first design iteration should produce polished versions of:

1. Login
2. Greenhouse list
3. Greenhouse detail — simulation not started
4. Greenhouse detail — simulation running
5. Greenhouse detail — completed/current state
6. Greenhouse historical view
7. Greenhouse with plant selected
8. Plant inspector / history
9. Empty / loading / error states where relevant

Do not build the chatbot yet.

---

# 46. Future Work — Natural-Language Greenhouse Assistant

A future version may contain a natural-language analytics assistant.

Possible questions:

```text
How much did we harvest last week?

Which plants require attention today?

Which plants have experienced recurring water stress?

What changed in this greenhouse since yesterday?

How much harvest should we expect this week?
```

The assistant should have access to greenhouse data through constrained APIs or SQL-generation tools.

It should not answer questions about source code.

This feature is deliberately outside the current frontend scope.

---

# 47. Future Work — Multi-Site Operations

Later versions may support:

```text
Organisation
    ↓
Sites
    ↓
Greenhouses
    ↓
Zones
    ↓
Plants
```

Potential interfaces:

- site overview
- cross-greenhouse workload
- production forecasts
- disease/attention heat maps
- labour planning
- greenhouse comparison

Do not implement these now.

---

# 48. Future Work — Real-Time Greenhouses

Real greenhouses should reuse the same detail page.

Differences:

Simulation greenhouse:

```text
Run simulation
Day 12 / 28
Simulation running
```

Real greenhouse:

```text
Live
Last update 18 seconds ago
```

Everything else should remain conceptually similar:

- greenhouse map
- plant state
- history
- insights
- recommendations
- timeline

This is an important design constraint.

---

# 49. What Not to Build

Do not spend time on:

- a 3D greenhouse
- photorealistic plants
- complicated map navigation
- drag-and-drop greenhouse editing
- chatbot
- advanced analytics builder
- admin panel
- billing
- permissions matrix
- complex onboarding wizard
- mobile-native navigation
- decorative landing-page marketing site

The POC should concentrate on the logged-in product experience.

---

# 50. Design Success Criteria

The design is successful if a first-time user can understand, without explanation:

1. they are looking at a greenhouse intelligence product;
2. they can choose among multiple greenhouses;
3. the selected greenhouse contains real plants represented spatially;
4. plant condition can change over time;
5. plants can be inspected individually;
6. current vs historical state is clear;
7. simulation is a data source, not the entire product concept;
8. operational priorities are visible;
9. the UI feels credible enough to evolve into a real commercial product.

---

# 51. Frontend Success Criteria

The generated frontend should:

- use React + TypeScript;
- use reusable shared components;
- centralize design tokens;
- centralize icons;
- centralize crop-specific visuals;
- avoid hard-coded 40-plant assumptions inside UI components;
- consume mock data through API-like boundaries;
- distinguish greenhouse domain concepts from simulation concepts;
- support more than one greenhouse;
- support historical snapshots;
- support plant selection;
- support progressive simulation state;
- keep the layout polished and coherent.

---

# 52. Suggested First Implementation Order

```text
1. Design tokens
2. Shared components
3. Crop / action / status icon system
4. App shell
5. Login
6. Greenhouse list
7. Greenhouse card
8. Greenhouse dashboard shell
9. Greenhouse map
10. Plant marker
11. Plant inspector
12. KPI area
13. Simulation controls
14. Simulation progress state
15. Timeline / historical navigation
16. Plant history
17. Charts
18. Recommendations
19. Empty / loading / error states
20. Responsive polish
```

---

# 53. Final Design Principle

The frontend should not look like a generic sensor dashboard with a greenhouse label added on top.

The crop, plant layout, plant history, harvest state, and operational priorities should give the product a recognizable greenhouse identity.

At the same time, avoid decorative complexity.

The key design idea is:

> **Make a complex biological and operational system feel understandable at a glance.**

A user should be able to open a greenhouse, visually understand its current condition, click into any plant, inspect what happened over time, and identify what deserves attention next.
