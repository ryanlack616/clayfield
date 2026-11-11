/**
 * mesh-forge contract types — authoritative.
 *
 * Every type named in README §4–§11 is defined here. C1 compiles this file
 * ("taxonomy types compile" is its exit criterion); C8a freezes the C1–C3
 * subset and generates `api-report.md` from it.
 *
 * Change policy after C8a: additive only, versioned, plus an ADR. Never rename
 * or remove a field in the frozen subset without a major version.
 */

/**
 * Minimal structural math types. `@mesh-forge/math` re-exports these later;
 * keeping them local means this file compiles before the packages exist (C0).
 */
export type Vec3 = readonly [number, number, number];
export type Mat4 = readonly [
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
];

/* ------------------------------------------------------------------ */
/* §4 — primitives and port types                                      */
/* ------------------------------------------------------------------ */

export type DType = 'u8' | 'u16' | 'f32';
export type NodeId = string;
export type JSONSchema = Record<string, unknown>;
export type ByteArray = Uint8Array | Uint16Array | Float32Array;

export interface ImageBuffer {
  readonly kind: 'image';
  readonly width: number;
  readonly height: number;
  readonly channels: 1 | 2 | 3 | 4;
  readonly dtype: DType;
  readonly data: ByteArray;
  readonly colorSpace: 'srgb' | 'linear';
}

export interface Field2D {
  readonly kind: 'field';
  readonly width: number;
  readonly height: number;
  readonly dtype: DType;
  readonly data: ByteArray;
}

/** Zero-copy window over a Field2D. Never owns memory. */
export interface FieldView {
  readonly kind: 'fieldView';
  readonly field: Field2D;
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
}

export interface MeshBuffers {
  readonly kind: 'mesh';
  readonly positions: Float32Array; // 3 floats per vertex
  readonly normals: Float32Array; // 3 floats per vertex
  readonly indices: Uint32Array; // 3 indices per triangle
  readonly vertexCount: number;
  readonly triangleCount: number;
}

export interface Ray {
  readonly origin: Vec3;
  readonly direction: Vec3;
}

export interface Hit {
  readonly distance: number;
  readonly point: Vec3;
  readonly normal: Vec3;
  readonly nodeId: NodeId | null;
  readonly triangleIndex: number | null;
}

export type Metrics = Readonly<Record<string, number>>;

export type PortType = ImageBuffer | Field2D | FieldView | MeshBuffers | Ray | Hit | Metrics;

/* ------------------------------------------------------------------ */
/* §4 — the six capability contracts                                   */
/* ------------------------------------------------------------------ */

export interface SourceAdapter<TOut extends PortType = PortType> {
  readonly id: string;
  readonly accepts: readonly string[]; // extensions / MIME types
  decode(input: Uint8Array | File, signal?: AbortSignal): Promise<TOut>;
}

/** Alias: an importer is a source adapter that reads a file. */
export type Importer = SourceAdapter;

export interface OperationDescriptor {
  readonly id: string;
  readonly version: number;
  readonly paramSchema: JSONSchema;
  readonly inputs: readonly PortType[];
  readonly outputs: readonly PortType[];
}

export interface OperationInstance {
  readonly descriptorId: string;
  readonly params: Readonly<Record<string, unknown>>;
  readonly enabled: boolean;
}

export type OperationSpec = readonly OperationInstance[];

export interface Operation {
  readonly descriptor: OperationDescriptor;
  apply(
    inputs: readonly PortType[],
    params: Readonly<Record<string, unknown>>,
    signal?: AbortSignal,
  ): Promise<PortType>;
}

export interface OperationRegistry {
  register(descriptor: OperationDescriptor): void;
  get(id: string): OperationDescriptor | undefined;
  list(): readonly OperationDescriptor[];
}

export interface Query {
  readonly id: string;
  run(ray: Ray, signal?: AbortSignal): Promise<readonly Hit[]>;
}

export interface Exporter {
  readonly id: string;
  readonly format: ExportFormat;
  export(inputs: readonly PortType[], sink: ExportSink, signal?: AbortSignal): Promise<void>;
}

export interface Analyzer {
  readonly id: string;
  run(inputs: readonly PortType[], signal?: AbortSignal): Promise<Metrics>;
}

export interface Pipeline {
  readonly stages: OperationSpec;
  run(input: PortType, options?: PipelineOptions): Promise<PortType>;
}

export interface PipelineOptions {
  readonly signal?: AbortSignal;
  readonly onProgress?: ProgressCallback;
  readonly budget?: ResourceBudget;
}

export interface ResourceBudget {
  readonly maxBytes: number;
  readonly maxMillis?: number;
  readonly maxPeakMemory?: number;
}

export interface ExportFormat {
  readonly id: string;
  readonly extensions: readonly string[];
  readonly mime: string;
}

export interface ExportSink {
  write(bytes: Uint8Array): Promise<void>;
  close(): Promise<void>;
}

export interface ExportJob {
  readonly id: string;
  readonly format: ExportFormat;
  readonly exporter: Exporter;
  readonly state: 'queued' | 'running' | 'done' | 'cancelled' | 'error';
  cancel(): void;
}

/* ------------------------------------------------------------------ */
/* §5 — units are app-side; core stays unitless                        */
/* ------------------------------------------------------------------ */

/**
 * Branded wrappers live in the app, not in core. Core only ever sees the
 * unitless Field2D. These are declared here so the boundary is written down.
 */
export type NormalizedField = Field2D & { readonly __brand: 'NormalizedField' };
export type Heightfield = Field2D & { readonly __brand: 'Heightfield' };

/* ------------------------------------------------------------------ */
/* §6 — document model                                                 */
/* ------------------------------------------------------------------ */

export interface Scene {
  readonly nodes: readonly Node[];
  readonly activeNodeId: NodeId | null;
  readonly selection: readonly NodeId[];
}

export interface Node {
  readonly id: NodeId;
  readonly kind: string;
  readonly name: string;
  readonly visible: boolean;
  readonly locked: boolean;
  readonly transform: Mat4;
  readonly parentId?: NodeId;
  readonly payload: unknown; // app-defined, validated by AppSchema
}

export interface DocumentEnvelope {
  readonly schemaId: string;
  readonly schemaVersion: number;
  readonly appId: string;
  readonly metadata: Readonly<Record<string, unknown>>;
  readonly scene: Scene;
  readonly revision: number;
}

/* ------------------------------------------------------------------ */
/* §7 — undo/redo                                                      */
/* ------------------------------------------------------------------ */

export interface Patch {
  readonly path: readonly (string | number)[];
  readonly before: unknown;
  readonly after: unknown;
}

export interface BlobRef {
  readonly id: string;
  readonly kind: string;
  readonly codec: string;
  readonly dtype?: DType;
  readonly shape?: readonly number[];
  readonly hash: string; // sha256 hex
  readonly byteLength: number;
}

export interface Command {
  readonly id: string;
  readonly label: string;
  readonly mergeKey?: string;
  readonly patches?: readonly Patch[];
  readonly blobs?: readonly BlobRef[];
  apply(doc: DocumentEnvelope): DocumentEnvelope;
  invert(doc: DocumentEnvelope): DocumentEnvelope;
}

export interface Transaction {
  readonly id: string;
  readonly label: string;
  readonly commands: readonly Command[];
}

export interface UndoManager {
  push(tx: Transaction): void;
  undo(): DocumentEnvelope | null;
  redo(): DocumentEnvelope | null;
  canUndo(): boolean;
  canRedo(): boolean;
  clear(): void;
  readonly maxCount: number;
  readonly maxBytes: number;
}

/* ------------------------------------------------------------------ */
/* §8 — transport and SAB                                              */
/* ------------------------------------------------------------------ */

export interface RpcEnvelope<T = unknown> {
  readonly id: number;
  readonly method: string;
  readonly params: T;
  readonly generation: number;
}

export interface JobHandle {
  readonly id: number;
  readonly generation: number;
}

export type GenerationToken = number;
export type CancelToken = number;

export interface Progress {
  readonly value: number;
  readonly total: number;
}

export type ProgressCallback = (progress: Progress) => void;
export type CancelCallback = (token: CancelToken) => void;

/** Little-endian, 8-byte aligned. Offsets are bytes from the SAB base. */
export interface ControlBlock {
  magic: number; // u32, 0x4d46_5342 ("MFSB")
  version: number; // u32
  generation: number; // u32, per-buffer
  cancel: number; // u32, 0 = run, 1 = cancel
  progress: number; // u32, 0..1000
  dirtyRectCount: number; // u32, max 16
  dirtyRects: Uint32Array; // 4 * 16 = 64 u32: x, y, w, h per rect
}

export interface SabLayout {
  readonly base: SharedArrayBuffer;
  readonly offsets: SharedArrayBuffer;
  readonly evaluated: SharedArrayBuffer;
  readonly display: SharedArrayBuffer;
  readonly control: SharedArrayBuffer; // holds one ControlBlock per buffer
}

/* ------------------------------------------------------------------ */
/* §9 — renderer plugin contract                                       */
/* ------------------------------------------------------------------ */

export interface DrawItem {
  readonly geometryHandle: number;
  readonly materialHandle: number;
  readonly transform: Mat4;
  readonly renderOrder: number;
  readonly pickable: boolean;
}

export interface SceneSnapshot {
  readonly drawList: readonly DrawItem[];
  readonly revision: number;
}

export interface Material {
  readonly id: string;
  readonly program: string; // GLSL source or registered program id
  readonly uniforms: Readonly<Record<string, UniformValue>>;
  readonly features: readonly string[];
  readonly depth: DepthState;
}

export type UniformValue = number | readonly number[] | Float32Array;

export interface DepthState {
  readonly test: boolean;
  readonly write: boolean;
  readonly func: 'less' | 'lequal' | 'always';
}

export interface Overlay {
  readonly id: string;
  readonly space: 'world' | 'screen';
  readonly kind: 'lines' | 'points';
  readonly depthTest: boolean;
}

export interface PickProvider {
  readonly id: string;
  pick(ray: Ray): Promise<readonly Hit[]>; // async: worker-backed queries
}

export interface MaterialRegistry {
  register(m: Material): void;
  get(id: string): Material | undefined;
}
export interface OverlayRegistry {
  register(o: Overlay): void;
  get(id: string): Overlay | undefined;
}
export interface PickProviderRegistry {
  register(p: PickProvider): void;
  get(id: string): PickProvider | undefined;
}

/* ------------------------------------------------------------------ */
/* §10 — persistence                                                   */
/* ------------------------------------------------------------------ */

export interface Manifest {
  readonly containerVersion: number;
  readonly appId: string;
  readonly schemaId: string;
  readonly schemaVersion: number;
  readonly blobs: readonly BlobRef[];
}

export interface BlobStore {
  get(id: string): Promise<Uint8Array | undefined>;
  put(id: string, bytes: Uint8Array): Promise<void>;
  list(): Promise<readonly BlobRef[]>;
  delete(id: string): Promise<void>;
}

export interface AppSchema {
  readonly schemaId: string;
  validate(doc: unknown): doc is DocumentEnvelope;
  migrate(doc: unknown, fromVersion: number): DocumentEnvelope;
}

export interface SchemaRegistry {
  register(schema: AppSchema): void;
  get(schemaId: string): AppSchema | undefined;
}

export interface MigrationRunner {
  run(doc: unknown, fromVersion: number, toVersion: number): Promise<DocumentEnvelope>;
}

/* ------------------------------------------------------------------ */
/* §11 — WASM ABI v1                                                   */
/* ------------------------------------------------------------------ */

/** u64: generation in the high 32 bits, index in the low 32. BigInt in JS. */
export type Handle = bigint;

export type ErrorCode = string; // "MF-<AREA>-<NNN>"

export interface Limits {
  readonly maxBuffers: number;
  readonly maxBufferBytes: number;
  readonly maxTotalBytes: number;
  readonly maxHandles: number;
}

export interface OpDescriptor {
  readonly id: string;
  readonly version: number;
  readonly inputTypes: readonly string[];
  readonly outputTypes: readonly string[];
}

export interface CapabilityManifest {
  readonly abiVersion: number;
  readonly coreVersion: string;
  readonly opsetVersion: number;
  readonly ops: readonly OpDescriptor[];
  readonly exportFormats: readonly string[];
  readonly limits: Limits;
}

export interface BulkBufferDescriptor {
  readonly ptr: number; // u32 byte offset into wasm memory
  readonly len: number; // u32 bytes
  readonly dtype: DType;
  readonly shape: readonly number[];
}

export interface ABI {
  init(hostApiVersion: number): ErrorCode | null;
  describe(): CapabilityManifest;
  alloc(bytes: number): Handle;
  free(handle: Handle): void;
  release(handle: Handle): ErrorCode | null;
  /** The single entry point for registered domain ops. */
  invoke(opId: string, paramsPtr: number, paramsLen: number): Handle;
}
