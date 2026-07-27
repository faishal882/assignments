# Design System

## Intent

An evidence room in bright daylight: crisp white work surface, decisive red annotations, dark ink, and cool blue data marks. The composition should feel like a product-ops decision memo pinned to a wall, with enough visual energy to be memorable and enough restraint to keep 100 records readable.

## Color

- Strategy: committed. Warm red carries the identity; blue is reserved for data and links.
- Background: `oklch(1 0 0)`
- Surface: `oklch(0.965 0 0)`
- Ink: `oklch(0.19 0.015 30)`
- Muted: `oklch(0.46 0.018 30)`
- Primary: `oklch(0.61 0.19 30)`
- Primary dark: `oklch(0.39 0.14 30)`
- Accent: `oklch(0.50 0.17 251)`
- Positive: `oklch(0.49 0.12 151)`
- Warning: `oklch(0.72 0.15 76)`

## Typography

Use Manrope as a single intentional family: 750-800 for decisive display copy, 600-700 for labels and table hierarchy, 400-500 for dense evidence. Numeric data uses tabular figures. Display tracking never tighter than `-0.035em`.

## Layout

- Maximum reading width: 1200px.
- Hero uses an asymmetric decision-summary layout, not a metric-card grid.
- Full-width horizontal portfolio bar carries the main quantitative story.
- Content alternates between broad narrative fields and dense audit tables.
- Section spacing varies from 64px to 128px to distinguish skim and audit modes.

## Components

- Verdict chips use text plus color; never color alone.
- Evidence links are explicit external links with provider labels.
- Table filters are native controls with visible focus and a result count.
- Process is a true ordered sequence, the only numbered scaffold on the page.
- Corrections use before/after pairs without nested cards.

## Motion

One initial portfolio-bar expansion and subtle filter-result transitions. All content is visible without animation; `prefers-reduced-motion` disables transforms and transitions.

## Responsive Behavior

At narrow widths, hero columns stack, charts preserve labels, table becomes horizontally scrollable with the app column sticky, and process steps become a vertical sequence. No horizontal overflow outside the explicit table scroller.
