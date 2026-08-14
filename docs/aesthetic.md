# The visual language

Measured from `reference/inspiration.jpg`, not guessed. Where a number appears
below it was sampled from that image.

## Two colours, and almost no ink

    ground   #CDC499     a flat sand/khaki
    ink      #000000

That is the entire palette. There is no third colour, no accent hue, no shadow
tint. The ground is used identically for the canvas, the top bar, the prose
panel and the sidebar — the panels are separated by hairlines, not by fills.
The sidebar alone is a barely-there step darker (`#C8C197`), which reads as a
seam rather than a panel.

**Ink covers 4.1% of the pixels.** That restraint is doing most of the work. Any
change that raises the ink share — heavier strokes, filled shapes, more labels —
moves it away from the reference faster than a wrong colour would.

Emphasis is achieved by *inversion*, never by colour: an inline highlight is a
black chip with sand text sitting in the run of prose.

## Everything is monospace

One family, one size for body text, with hierarchy carried by letter-spacing
and case rather than by weight or scale. Section headings are small, widely
tracked, uppercase. The only large type on the page is the single title in the
prose panel.

## Projection

True isometric, drawn as line art. Blocks are extruded rectangles:

- **Top faces** are empty ground — no fill.
- **Side faces** carry fine diagonal hatching. This is the only texture in the
  system and it is what makes the blocks read as solid.
- **Edges** are single-weight black lines. No outline hierarchy, no thick/thin
  distinction between silhouette and interior.

A faint grid sits on the ground plane, visible only where nothing covers it.

### Height means something

From the reference's own prose: *"The tall structures are the measuring parts."*
Extrusion height is a data channel, not decoration. Whatever it maps to must be
stated in the panel, or the reader will invent a meaning for it.

Two block variants appear:

- **Stacked plates** (the `P` block) — several thin layers instead of one solid
  extrusion, for something that is a collection of many like things.
- **Clustered runs** (the `D` group) — a row of narrow blocks sharing a
  footprint, for a set of parallel instances.

## Edges and flow

Connections are thin black polylines routed orthogonally in isometric space.
Small solid **diamonds** sit along an edge; these are the flow markers, and
animating them along the path is what "the flow" means.

**Dashed** lines mean a different class of relationship from solid ones — in the
reference they enclose or connect things that are present but not switched on.
Whatever the distinction ends up being, it needs to be in the legend.

## Layout regions

    ┌──────────────────────────────────────────────┬─────────────────┐
    │ repo name · variant │ stat │ stat │ stat      │ [flow controls] │
    ├──────────┬───────────────────────────────────┴─────────────────┤
    │ sidebar  │ isometric canvas          │ prose panel             │
    │ (keyed   │                           │ (tabbed)                │
    │  index)  │                           │                         │
    ├──────────┴───────────────────────────┴─────────────────────────┤
    │ → GO INSIDE · ← COME BACK OUT · ↓↑ MOVE · HOVER · DRAG · SCROLL │
    └─────────────────────────────────────────────────────────────────┘

**Top bar** — repository identity on the left, then a row of counted facts about
the system, each with a tracked uppercase label above a value.

**Sidebar** — a hierarchical index. Each entry has a single-letter or short key
matching the label on its block, a name, and a count on the right. Indentation
carries nesting. Group headings (`THE SYSTEM`, `THE GAME`, `WHAT COMES OUT`) are
plain tracked text with no box.

**Prose panel** — tabs (`WHAT IT DOES` / `HOW IT'S BUILT`), an eyebrow, a serif-
weight title in mono, then body prose with inverted inline highlights. This is
where the system gets *explained*; the diagram is deliberately underlabelled
because this panel carries the words.

**Hint bar** — the full interaction vocabulary spelled out in one line, in the
same tracked uppercase as everything else. Nothing is hidden behind discovery.

## Interaction vocabulary

    →  GO INSIDE        descend into a block, revealing its internals as a new map
    ←  COME BACK OUT    ascend one level
    ↓↑ MOVE             move the selection between blocks at this level
       HOVER TO READ    a plain-language description, without clicking
       DRAG TO PAN
       SCROLL TO ZOOM

    RESUME THE FLOW     run the execution animation
    TRACE ONE STEP      advance exactly one hop, and hold
    RESET VIEW          back to the default camera

`TRACE ONE STEP` is the one that makes this a tool rather than a picture: it
lets a reader walk a path at their own pace and read each hop.

## The rule that matters most

Every element in the reference either names something or measures something.
Nothing is present for decoration — there is no gradient, no glow, no rounded
corner, no drop shadow, no icon. When adding anything, the test is: *what fact
does this encode?* If there is no answer, it does not go in.
