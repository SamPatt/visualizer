# Working in this repository

## What this is

A tool that reads a codebase and renders it as an isometric map with execution
flowing through it. See `README.md` for intent and `docs/aesthetic.md` for the
visual specification.

Nothing is implemented yet. Before writing code, read `docs/decisions.md` — it
lists the choices that have not been made, and picking one silently is worse
than asking.

## The aesthetic is the product

This is not a diagram with a theme applied; the restraint *is* the design.
`docs/aesthetic.md` records values measured from the reference image, including
the ink coverage figure. Two rules matter more than the rest:

- **Two colours only** — ground `#CDC499`, ink black. Emphasis is inversion, not
  hue. No accent colour, no gradient, no shadow, no rounded corner, no icon.
- **Every element names something or measures something.** Before adding any
  visual element, answer: what fact does this encode? If there is no answer, it
  does not go in.

If a change would raise the proportion of the canvas covered in ink, say so
explicitly when proposing it.

## Verify what you claim

Claims about the rendered output should be checked against the rendered output,
not against the code that was supposed to produce it. If you generate an image
or a page, look at it before reporting that it works.

## Reference

`docs/reference/inspiration.jpg` is the target. It is a mock-up — no code in
this repository produced it. Do not treat it as a screenshot of working
software, and do not describe the tool as doing something merely because the
mock-up depicts it.
