// Boundary rules from mesh-forge/README.md §12. Run with:
//   pnpm lint:boundaries
module.exports = {
  forbidden: [
    {
      name: 'no-circular',
      severity: 'error',
      comment: 'Circular dependency',
      from: {},
      to: { circular: true },
    },
    {
      name: 'no-clayfield-in-core',
      severity: 'error',
      comment: 'Core never imports the app (README §12)',
      from: { path: '^(packages|apps)/' },
      to: { path: '^@clayfield/' },
    },
    {
      name: 'no-deep-imports',
      severity: 'error',
      comment: 'Import package roots only; no deep paths',
      from: { path: '^(packages|apps)/' },
      to: { path: '^@mesh-forge/[^/]+/' },
    },
    {
      name: 'edge-math',
      severity: 'error',
      comment:
        '@mesh-forge/math may not import @mesh-forge/buffers, @mesh-forge/geometry, @mesh-forge/document, @mesh-forge/render, @mesh-forge/viewport-react, @mesh-forge/export, @mesh-forge/transport, @mesh-forge/persistence, @mesh-forge/wasm-host, @mesh-forge/ui (README §12)',
      from: { path: '^packages/math/' },
      to: {
        path: '^@mesh-forge/(buffers|geometry|document|render|viewport-react|export|transport|persistence|wasm-host|ui)',
      },
    },
    {
      name: 'edge-buffers',
      severity: 'error',
      comment:
        '@mesh-forge/buffers may not import @mesh-forge/geometry, @mesh-forge/document, @mesh-forge/render, @mesh-forge/viewport-react, @mesh-forge/export, @mesh-forge/transport, @mesh-forge/persistence, @mesh-forge/wasm-host, @mesh-forge/ui (README §12)',
      from: { path: '^packages/buffers/' },
      to: {
        path: '^@mesh-forge/(geometry|document|render|viewport-react|export|transport|persistence|wasm-host|ui)',
      },
    },
    {
      name: 'edge-geometry',
      severity: 'error',
      comment:
        '@mesh-forge/geometry may not import @mesh-forge/document, @mesh-forge/render, @mesh-forge/viewport-react, @mesh-forge/export, @mesh-forge/transport, @mesh-forge/persistence, @mesh-forge/wasm-host, @mesh-forge/ui (README §12)',
      from: { path: '^packages/geometry/' },
      to: {
        path: '^@mesh-forge/(document|render|viewport-react|export|transport|persistence|wasm-host|ui)',
      },
    },
    {
      name: 'edge-document',
      severity: 'error',
      comment:
        '@mesh-forge/document may not import @mesh-forge/render, @mesh-forge/viewport-react, @mesh-forge/export, @mesh-forge/transport, @mesh-forge/persistence, @mesh-forge/wasm-host, @mesh-forge/ui (README §12)',
      from: { path: '^packages/document/' },
      to: {
        path: '^@mesh-forge/(render|viewport-react|export|transport|persistence|wasm-host|ui)',
      },
    },
    {
      name: 'edge-render',
      severity: 'error',
      comment:
        '@mesh-forge/render may not import @mesh-forge/document, @mesh-forge/viewport-react, @mesh-forge/export, @mesh-forge/transport, @mesh-forge/persistence, @mesh-forge/wasm-host, @mesh-forge/ui (README §12)',
      from: { path: '^packages/render/' },
      to: {
        path: '^@mesh-forge/(document|viewport-react|export|transport|persistence|wasm-host|ui)',
      },
    },
    {
      name: 'edge-viewport-react',
      severity: 'error',
      comment:
        '@mesh-forge/viewport-react may not import @mesh-forge/document, @mesh-forge/export, @mesh-forge/transport, @mesh-forge/persistence, @mesh-forge/wasm-host, @mesh-forge/ui (README §12)',
      from: { path: '^packages/viewport-react/' },
      to: { path: '^@mesh-forge/(document|export|transport|persistence|wasm-host|ui)' },
    },
    {
      name: 'edge-export',
      severity: 'error',
      comment:
        '@mesh-forge/export may not import @mesh-forge/document, @mesh-forge/render, @mesh-forge/viewport-react, @mesh-forge/transport, @mesh-forge/persistence, @mesh-forge/wasm-host, @mesh-forge/ui (README §12)',
      from: { path: '^packages/export/' },
      to: {
        path: '^@mesh-forge/(document|render|viewport-react|transport|persistence|wasm-host|ui)',
      },
    },
    {
      name: 'edge-transport',
      severity: 'error',
      comment:
        '@mesh-forge/transport may not import @mesh-forge/geometry, @mesh-forge/document, @mesh-forge/render, @mesh-forge/viewport-react, @mesh-forge/export, @mesh-forge/persistence, @mesh-forge/wasm-host, @mesh-forge/ui (README §12)',
      from: { path: '^packages/transport/' },
      to: {
        path: '^@mesh-forge/(geometry|document|render|viewport-react|export|persistence|wasm-host|ui)',
      },
    },
    {
      name: 'edge-persistence',
      severity: 'error',
      comment:
        '@mesh-forge/persistence may not import @mesh-forge/geometry, @mesh-forge/render, @mesh-forge/viewport-react, @mesh-forge/export, @mesh-forge/transport, @mesh-forge/wasm-host, @mesh-forge/ui (README §12)',
      from: { path: '^packages/persistence/' },
      to: { path: '^@mesh-forge/(geometry|render|viewport-react|export|transport|wasm-host|ui)' },
    },
    {
      name: 'edge-wasm-host',
      severity: 'error',
      comment:
        '@mesh-forge/wasm-host may not import @mesh-forge/geometry, @mesh-forge/document, @mesh-forge/render, @mesh-forge/viewport-react, @mesh-forge/export, @mesh-forge/transport, @mesh-forge/persistence, @mesh-forge/ui (README §12)',
      from: { path: '^packages/wasm-host/' },
      to: {
        path: '^@mesh-forge/(geometry|document|render|viewport-react|export|transport|persistence|ui)',
      },
    },
    {
      name: 'edge-ui',
      severity: 'error',
      comment:
        '@mesh-forge/ui may not import @mesh-forge/math, @mesh-forge/buffers, @mesh-forge/geometry, @mesh-forge/document, @mesh-forge/render, @mesh-forge/viewport-react, @mesh-forge/export, @mesh-forge/transport, @mesh-forge/persistence, @mesh-forge/wasm-host (README §12)',
      from: { path: '^packages/ui/' },
      to: {
        path: '^@mesh-forge/(math|buffers|geometry|document|render|viewport-react|export|transport|persistence|wasm-host)',
      },
    },
  ],
  options: {
    doNotFollow: { path: 'node_modules' },
    tsConfig: { fileName: 'tsconfig.json' },
    enhancedResolveOptions: { exportsFields: ['exports'], conditionNames: ['import', 'types'] },
    reporterOptions: { dot: { collapsePattern: 'node_modules/[^/]+' } },
  },
};
