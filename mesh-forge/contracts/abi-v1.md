# WASM ABI v1 — wire layout

The TS mirror of these types is in [`types.ts`](types.ts). This file is the
byte-level contract between `mesh-forge-wasm` (Rust) and `@mesh-forge/wasm-host`
(TS). Freeze at C8a; change only by additive amendment plus an ADR.

Little-endian. All structs 8-byte aligned. No Rust strings or trait objects cross
the boundary — strings travel as `(ptr: u32, len: u32)` into the same memory.

## Version numbers

`version.json` in this directory holds all four. They move independently.

| Number | Meaning | Bumped when |
|---|---|---|
| `ABI_VERSION` | wire layout | struct/field changes |
| `CORE_VERSION` | `mesh-forge-core` release | any core release |
| `OPSET_VERSION` | registered op set | ops added/removed |
| `OP_VERSION` | per-op semantics | an op's output changes |

## Structs

### `CapabilityManifest` (returned by `describe()`)

| Offset | Type | Field |
|---|---|---|
| 0 | u32 | `abiVersion` |
| 4 | u32 | `coreVersionPtr` |
| 8 | u32 | `coreVersionLen` |
| 12 | u32 | `opsetVersion` |
| 16 | u32 | `opsPtr` |
| 20 | u32 | `opsCount` |
| 24 | u32 | `formatsPtr` |
| 28 | u32 | `formatsCount` |
| 32 | u32 | `maxBuffers` |
| 36 | u32 | `maxBufferBytes` |
| 40 | u64 | `maxTotalBytes` |
| 48 | u32 | `maxHandles` |

Total 52 bytes, padded to 56.

### `OpDescriptor` (array element, 28 bytes; 4-byte aligned)

| Offset | Type | Field |
|---|---|---|
| 0 | u32 | `idPtr` |
| 4 | u32 | `idLen` |
| 8 | u32 | `version` |
| 12 | u32 | `inputTypesPtr` |
| 16 | u32 | `inputTypesLen` |
| 20 | u32 | `outputTypesPtr` |
| 24 | u32 | `outputTypesLen` |

### `BulkBufferDescriptor` (24 bytes)

| Offset | Type | Field |
|---|---|---|
| 0 | u32 | `ptr` |
| 4 | u32 | `len` |
| 8 | u32 | `dtype` (0=u8, 1=u16, 2=f32) |
| 12 | u32 | `shapePtr` |
| 16 | u32 | `shapeLen` |
| 20 | u32 | reserved |

### `Handle` (u64)

Generation in the high 32 bits, index in the low 32. Crosses the JS boundary as
`BigInt`. Memory growth detaches raw pointers and typed-array views; handles stay
valid.

## Functions

```c
// Returns 0 on success, else an MF-* error code as a u32 index into the
// error table; the host maps it to a string.
u32   init(u32 hostApiVersion);
u32   describe(void);              // ptr to CapabilityManifest
u64   alloc(u32 bytes);
u32   free(u64 handle);
u32   release(u64 handle);
u64   invoke(u32 opIdPtr, u32 opIdLen, u32 paramsPtr, u32 paramsLen);
```

`invoke` is the single entry point for registered domain ops. A returned handle
is owned by the caller and released with `release`.

## Error codes

Core codes are `MF-<AREA>-<NNN>` and are mapped to app-facing `CF-*` codes at
the host boundary. See [`../../docs/reference/error-codes.md`](../../docs/reference/error-codes.md).

## Control block (SAB)

Not part of the ABI function surface — it is a shared memory region. Layout is
in [`../README.md` §8](../README.md) and mirrored as `ControlBlock` in
`types.ts`. One block per buffer; each block has its own generation counter.
