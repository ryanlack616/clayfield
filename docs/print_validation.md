# Print QA

The repeatable local print QA command is:

```sh
CLAYFIELD_PRUSA_SLICER=/path/to/prusa-slicer \
.venv/bin/python benchmarks/print_qa.py
```

It generates a 60 × 40 × 8 mm positive-relief STL and 3MF tile under
`dist/print-qa/`, checks each with PrusaSlicer, and writes G-code alongside the
models. The current development host generated and sliced both formats
successfully. This is a digital printability check; physical dimensions,
adhesion, surface detail, and ceramic behavior still require a real printer.

The current generated files are:

- `dist/print-qa/clayfield-qa.stl`
- `dist/print-qa/clayfield-qa.3mf`
- `dist/print-qa/clayfield-qa-stl.gcode`
- `dist/print-qa/clayfield-qa-3mf.gcode`

Both models report 60 × 40 × 8 mm, one manifold part, and successful slicing.
