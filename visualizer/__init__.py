"""Read a codebase, draw it as an isometric map you can walk through.

The pipeline is one direction, and each stage knows only the stage before it:

    analyze   read the source without running it
    tracing   optionally record a real run over the same source
    manifest  fold both into a Scene, guided by checked-in judgement
    layout    place the blocks and route the edges
    render    draw the plane as line art
    page      wrap it in one self-contained HTML file
"""

__all__ = ["analyze", "iso", "layout", "manifest", "model", "page", "render", "tracing"]
__version__ = "0.1.0"
