//! mesh-forge-core: domain-agnostic buffers, transform ops, pipeline execution,
//! cancellation/progress budgets, export sink, ABI descriptors.
//!
//! Must not depend on any domain crate. Enforced by `cargo deny` in CI.

/// Crate version, mirrored into the capability manifest.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// ABI version this core speaks. Bumped on any wire-layout change.
pub const ABI_VERSION: u32 = 1;

#[cfg(test)]
mod tests {
    #[test]
    fn version_is_present() {
        assert!(!super::VERSION.is_empty());
        assert_eq!(super::ABI_VERSION, 1);
    }
}
