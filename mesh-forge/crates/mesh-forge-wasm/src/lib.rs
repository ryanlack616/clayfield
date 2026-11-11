//! mesh-forge-wasm: thin ABI crate over mesh-forge-core.
//! `#[repr(C)]` POD descriptors, bytemuck helpers, handle ABI, capability aggregation.
//! No domain ops live here.

pub use mesh_forge_core::{ABI_VERSION, VERSION};

/// The handle ABI: generation in the high 32 bits, index in the low 32.
pub type Handle = u64;

/// Split a handle into (generation, index).
pub const fn split_handle(h: Handle) -> (u32, u32) {
    ((h >> 32) as u32, (h & 0xffff_ffff) as u32)
}

/// Compose a handle from (generation, index).
pub const fn make_handle(generation: u32, index: u32) -> Handle {
    ((generation as u64) << 32) | (index as u64)
}

#[cfg(test)]
mod tests {
    #[test]
    fn handle_round_trip() {
        let h = super::make_handle(7, 42);
        assert_eq!(super::split_handle(h), (7, 42));
    }
}
