# Comfortzone EX dashboard concepts

All four concepts use the same basic flow: room exhaust air enters the heat
pump, passes the evaporator and leaves as cooled exhaust air; the refrigerant
circuit drives the condenser, which supplies domestic hot water and the
heating circuit. Text and live readings are intentionally omitted so Home
Assistant cards can be positioned above the selected background.

1. `01-dark-blueprint.png` — restrained navy technical schematic with luminous
   functional paths.
   - `01-dark-blueprint-no-radiator.png` — first controlled revision with only
     the radiator and its dedicated pipe branch removed.
   - `01-dark-blueprint-no-radiator-1og-bath.png` — additionally replaces the
     first-floor bedroom with a bathroom.
   - `01-dark-blueprint-flow-corrected.png` — dashboard-ready revision with
     the corrected exhaust-air, hot-water supply, and hot-water return flow
     directions.
2. `02-light-material.png` — bright, minimal Scandinavian/Material-style
   illustration with strong legibility.
3. `03-warm-architectural.png` — residential cutaway with warm materials and
   prepared empty callout areas.
4. `04-dark-glass.png` — premium dark glassmorphism with dimensional equipment
   and glowing energy paths.

The selected direction should be refined before integration: correct the exact
Comfortzone EX hydraulic arrangement, reserve fixed anchors for every entity,
and crop or extend it to the target dashboard aspect ratio.
