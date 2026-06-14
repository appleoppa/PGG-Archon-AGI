use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
type PyObject = Py<PyAny>;
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};

// ─── Module constants ───

const SURFACE_VERSION: &str = "PGGArchonSecurityPolicySurface/v1";
const SURFACE_SOURCE: &str = "APEX-AGI hypercore/src/security.rs";

// ─── SecurityRing ───

#[repr(i32)]
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
enum SecurityRingRepr {
    Kernel = 0,
    Hypervisor = 1,
    Supervisor = 2,
    User = 3,
}

impl SecurityRingRepr {
    fn from_i32(v: i32) -> Option<Self> {
        match v {
            0 => Some(Self::Kernel),
            1 => Some(Self::Hypervisor),
            2 => Some(Self::Supervisor),
            3 => Some(Self::User),
            _ => None,
        }
    }

    fn name(&self) -> &'static str {
        match self {
            Self::Kernel => "Kernel",
            Self::Hypervisor => "Hypervisor",
            Self::Supervisor => "Supervisor",
            Self::User => "User",
        }
    }
}

#[pyclass(eq, eq_int)]
#[derive(Clone, Copy, Debug, PartialEq)]
enum PySecurityRing {
    Kernel = 0,
    Hypervisor = 1,
    Supervisor = 2,
    User = 3,
}

#[pymethods]
impl PySecurityRing {
    #[new]
    fn py_new(value: i32) -> PyResult<Self> {
        match value {
            0 => Ok(Self::Kernel),
            1 => Ok(Self::Hypervisor),
            2 => Ok(Self::Supervisor),
            3 => Ok(Self::User),
            _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Invalid SecurityRing value: {}. Must be 0-3.",
                value
            ))),
        }
    }

    fn __int__(&self) -> i32 {
        *self as i32
    }

    fn __repr__(&self) -> String {
        format!("<SecurityRing.{}: {}>", self.name_str(), *self as i32)
    }

    fn __str__(&self) -> String {
        self.name_str().to_string()
    }

    #[getter]
    fn name(&self) -> String {
        self.name_str().to_string()
    }

    #[getter]
    fn value(&self) -> i32 {
        *self as i32
    }
}

impl PySecurityRing {
    fn name_str(&self) -> &'static str {
        match self {
            Self::Kernel => "Kernel",
            Self::Hypervisor => "Hypervisor",
            Self::Supervisor => "Supervisor",
            Self::User => "User",
        }
    }
}

fn ring_name(ring: i32) -> String {
    match SecurityRingRepr::from_i32(ring) {
        Some(r) => r.name().to_string(),
        None => format!("Unknown({})", ring),
    }
}

// ─── Capability ───

#[pyclass(get_all, set_all)]
#[derive(Clone, Debug, Serialize, Deserialize)]
struct Capability {
    #[pyo3(name = "id")]
    id: String,
    description: String,
    min_ring: i32,
    scope: String,
}

#[pymethods]
impl Capability {
    #[new]
    #[pyo3(signature = (id, description, min_ring=3, scope="".to_string()))]
    fn py_new(id: String, description: String, min_ring: i32, scope: String) -> Self {
        Self {
            id,
            description,
            min_ring,
            scope,
        }
    }

    fn accessible_by(&self, ring: i32) -> bool {
        ring <= self.min_ring
    }

    fn to_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
        let d = PyDict::new(py);
        d.set_item("id", &self.id)?;
        d.set_item("description", &self.description)?;
        d.set_item("min_ring", self.min_ring)?;
        d.set_item("scope", &self.scope)?;
        Ok(d.into())
    }

    fn __repr__(&self) -> String {
        format!(
            "Capability(id={:?}, description={:?}, min_ring={}, scope={:?})",
            self.id, self.description, self.min_ring, self.scope
        )
    }

    fn __str__(&self) -> String {
        format!("Capability({})", self.id)
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.id == other.id
            && self.description == other.description
            && self.min_ring == other.min_ring
            && self.scope == other.scope
    }
}

// ─── CapabilitySet ───

#[pyclass]
#[derive(Clone, Debug)]
struct CapabilitySet {
    capabilities: Vec<Capability>,
}

#[pymethods]
impl CapabilitySet {
    #[new]
    #[pyo3(signature = (capabilities=None))]
    fn py_new(capabilities: Option<Vec<Capability>>) -> Self {
        Self {
            capabilities: capabilities.unwrap_or_default(),
        }
    }

    fn has(&self, capability_id: &str) -> bool {
        self.capabilities.iter().any(|c| c.id == capability_id)
    }

    fn check(&self, capability_id: &str, ring: i32) -> bool {
        self.capabilities
            .iter()
            .find(|c| c.id == capability_id)
            .map(|c| c.accessible_by(ring))
            .unwrap_or(false)
    }

    fn by_scope(&self, prefix: &str) -> Self {
        let matching: Vec<Capability> = self
            .capabilities
            .iter()
            .filter(|c| c.scope.starts_with(prefix))
            .cloned()
            .collect();
        Self {
            capabilities: matching,
        }
    }

    fn merge(&self, other: &Self) -> Self {
        let mut merged = self.capabilities.clone();
        let existing_ids: std::collections::HashSet<&str> =
            self.capabilities.iter().map(|c| c.id.as_str()).collect();
        for c in &other.capabilities {
            if !existing_ids.contains(c.id.as_str()) {
                merged.push(c.clone());
            }
        }
        Self {
            capabilities: merged,
        }
    }

    fn to_dicts(&self, py: Python<'_>) -> PyResult<Vec<PyObject>> {
        let mut result = Vec::with_capacity(self.capabilities.len());
        for c in &self.capabilities {
            result.push(c.to_dict(py)?);
        }
        Ok(result)
    }

    fn __len__(&self) -> usize {
        self.capabilities.len()
    }

    fn __repr__(&self) -> String {
        format!("CapabilitySet({} capabilities)", self.capabilities.len())
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyResult<Py<CapabilitySetIter>> {
        let iter = CapabilitySetIter {
            inner: slf.capabilities.clone(),
            index: 0,
        };
        Py::new(slf.py(), iter)
    }
}

#[pyclass]
struct CapabilitySetIter {
    inner: Vec<Capability>,
    index: usize,
}

#[pymethods]
impl CapabilitySetIter {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<Capability> {
        if slf.index < slf.inner.len() {
            let item = slf.inner[slf.index].clone();
            slf.index += 1;
            Some(item)
        } else {
            None
        }
    }
}

// ─── SecurityContext ───

#[pyclass]
#[derive(Clone, Debug)]
struct SecurityContext {
    ring: i32,
    capabilities: CapabilitySet,
    sandboxed: bool,
}

#[pymethods]
impl SecurityContext {
    #[new]
    #[pyo3(signature = (ring=3, capabilities=None, sandboxed=true))]
    fn py_new(ring: i32, capabilities: Option<CapabilitySet>, sandboxed: bool) -> Self {
        Self {
            ring,
            capabilities: capabilities.unwrap_or(CapabilitySet::py_new(None)),
            sandboxed,
        }
    }

    fn can(&self, capability_id: &str) -> bool {
        self.capabilities.check(capability_id, self.ring)
    }

    #[getter]
    fn get_ring(&self) -> i32 {
        self.ring
    }

    #[setter]
    fn set_ring(&mut self, ring: i32) {
        self.ring = ring;
    }

    #[getter]
    fn get_capabilities(&self) -> CapabilitySet {
        self.capabilities.clone()
    }

    #[setter]
    fn set_capabilities(&mut self, capabilities: CapabilitySet) {
        self.capabilities = capabilities;
    }

    #[getter]
    fn get_sandboxed(&self) -> bool {
        self.sandboxed
    }

    #[setter]
    fn set_sandboxed(&mut self, sandboxed: bool) {
        self.sandboxed = sandboxed;
    }

    fn __repr__(&self) -> String {
        format!(
            "SecurityContext(ring={}, sandboxed={}, {} capabilities)",
            self.ring,
            self.sandboxed,
            self.capabilities.capabilities.len()
        )
    }

    fn to_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
        let d = PyDict::new(py);
        d.set_item("ring", self.ring)?;
        d.set_item("sandboxed", self.sandboxed)?;
        d.set_item("capability_count", self.capabilities.capabilities.len())?;
        Ok(d.into())
    }
}

// ─── build_security_policy_surface — the main exported function ───

#[pyfunction]
#[pyo3(signature = (context=None))]
fn build_pgg_archon_security_policy_surface(
    py: Python<'_>,
    context: Option<PyObject>,
) -> PyResult<PyObject> {
    let now_ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let created_at = format_timestamp(now_ts);

    let d = PyDict::new(py);
    d.set_item("schema", SURFACE_VERSION)?;
    d.set_item("source", SURFACE_SOURCE)?;
    d.set_item("created_at", &created_at)?;
    d.set_item("agi_completion_claim", false)?;
    d.set_item(
        "boundary",
        "Read-only security policy surface. No model calls, no gene writes, no daemon starts.",
    )?;

    let context = match context {
        Some(c) => c.extract::<Py<PyDict>>(py).ok(),
        None => None,
    };

    let ctx = match &context {
        Some(c) => c.bind(py).clone(),
        None => {
            d.set_item("status", "WATCH")?;
            d.set_item("ring", py.None())?;
            d.set_item("ring_name", "Unknown")?;
            d.set_item("sandboxed", py.None())?;
            d.set_item("capability_count", 0)?;
            d.set_item("warnings", vec!["SecurityContextMissing"])?;
            d.set_item("failures", vec![] as Vec<String>)?;
            return Ok(d.into());
        }
    };

    let ring: i32 = ctx
        .get_item("ring")
        .ok()
        .flatten()
        .and_then(|v| v.extract::<i32>().ok())
        .unwrap_or(3);
    let sandboxed: bool = ctx
        .get_item("sandboxed")
        .ok()
        .flatten()
        .and_then(|v| v.extract::<bool>().ok())
        .unwrap_or(true);

    let raw_caps: Vec<PyObject> = ctx
        .get_item("capabilities")
        .ok()
        .flatten()
        .and_then(|v| v.extract::<Vec<PyObject>>().ok())
        .unwrap_or_default();

    let capabilities: Vec<Capability> = raw_caps
        .iter()
        .filter_map(|cap_obj| {
            let cap_py: Py<PyDict> = cap_obj.extract::<Py<PyDict>>(py).ok()?;
            let cap_dict = cap_py.bind(py);
            Some(Capability {
                id: cap_dict
                    .get_item("id")
                    .ok()
                    .flatten()
                    .and_then(|v| v.extract::<String>().ok())
                    .unwrap_or_default(),
                description: cap_dict
                    .get_item("description")
                    .ok()
                    .flatten()
                    .and_then(|v| v.extract::<String>().ok())
                    .unwrap_or_default(),
                min_ring: cap_dict
                    .get_item("min_ring")
                    .ok()
                    .flatten()
                    .and_then(|v| v.extract::<i32>().ok())
                    .unwrap_or(3),
                scope: cap_dict
                    .get_item("scope")
                    .ok()
                    .flatten()
                    .and_then(|v| v.extract::<String>().ok())
                    .unwrap_or_default(),
            })
        })
        .collect();

    // Determine status
    let (status, warnings, failures): (&str, Vec<String>, Vec<String>) =
        if ring == PySecurityRing::Kernel as i32 && !sandboxed {
            ("PASS", vec![], vec![])
        } else if ring == PySecurityRing::User as i32 && sandboxed {
            ("PASS", vec![], vec![])
        } else {
            (
                "WATCH",
                vec![format!(
                    "UnusualSecurityContext:ring={} sandboxed={}",
                    ring, sandboxed
                )],
                vec![],
            )
        };

    d.set_item("status", status)?;
    d.set_item("ring", ring)?;
    d.set_item("ring_name", ring_name(ring))?;
    d.set_item("sandboxed", sandboxed)?;
    d.set_item("capability_count", capabilities.len())?;

    // Build capabilities as dict list
    let caps_py: Vec<PyObject> = capabilities
        .iter()
        .filter_map(|c| c.to_dict(py).ok())
        .collect();
    d.set_item("capabilities", caps_py)?;
    d.set_item("warnings", warnings)?;
    d.set_item("failures", failures)?;

    Ok(d.into())
}

fn format_timestamp(unix_secs: u64) -> String {
    // Simple UTC timestamp without chrono dependency
    let secs_per_day: u64 = 86400;
    let days = unix_secs / secs_per_day;
    let rem = unix_secs % secs_per_day;
    let hours = rem / 3600;
    let minutes = (rem % 3600) / 60;
    let seconds = rem % 60;

    // Days since epoch (1970-01-01)
    let mut y = 1970i64;
    let mut d = days as i64;
    loop {
        let days_in_year = if is_leap(y) { 366 } else { 365 };
        if d < days_in_year {
            break;
        }
        d -= days_in_year;
        y += 1;
    }
    let (m, day) = ymd_from_doy(y, d);
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}+0000",
        y, m, day, hours, minutes, seconds
    )
}

fn is_leap(y: i64) -> bool {
    (y % 4 == 0 && y % 100 != 0) || y % 400 == 0
}

fn ymd_from_doy(year: i64, doy: i64) -> (u32, u32) {
    let days_in_months = if is_leap(year) {
        [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    } else {
        [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    };
    let mut remaining = doy;
    for (i, &days) in days_in_months.iter().enumerate() {
        if remaining < days {
            return ((i + 1) as u32, (remaining + 1) as u32);
        }
        remaining -= days;
    }
    (12, 31)
}

// ─── Tests ───

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_security_ring_values() {
        assert_eq!(SecurityRingRepr::Kernel as i32, 0);
        assert_eq!(SecurityRingRepr::Hypervisor as i32, 1);
        assert_eq!(SecurityRingRepr::Supervisor as i32, 2);
        assert_eq!(SecurityRingRepr::User as i32, 3);
    }

    #[test]
    fn test_security_ring_from_i32() {
        assert_eq!(SecurityRingRepr::from_i32(0), Some(SecurityRingRepr::Kernel));
        assert_eq!(SecurityRingRepr::from_i32(3), Some(SecurityRingRepr::User));
        assert_eq!(SecurityRingRepr::from_i32(4), None);
    }

    #[test]
    fn test_security_ring_name() {
        assert_eq!(ring_name(0), "Kernel");
        assert_eq!(ring_name(3), "User");
        assert_eq!(ring_name(99), "Unknown(99)");
    }

    #[test]
    fn test_capability_create() {
        let c = Capability {
            id: "test.write".into(),
            description: "Write test data".into(),
            min_ring: 2,
            scope: "test".into(),
        };
        assert_eq!(c.id, "test.write");
        assert_eq!(c.min_ring, 2);
    }

    #[test]
    fn test_capability_accessible_by() {
        // Kernel (0) can access anything
        let c = Capability {
            id: "admin".into(),
            description: "Admin access".into(),
            min_ring: 0,
            scope: "".into(),
        };
        assert!(c.accessible_by(0)); // Kernel
        assert!(!c.accessible_by(1)); // Hypervisor — 1 > 0 min_ring

        // User-level capability (min_ring=3)
        let c2 = Capability {
            id: "read".into(),
            description: "Read access".into(),
            min_ring: 3,
            scope: "".into(),
        };
        assert!(c2.accessible_by(0)); // Kernel
        assert!(c2.accessible_by(3)); // User
        assert!(!c2.accessible_by(4)); // Outside range
    }

    #[test]
    fn test_capability_to_dict() {
        let c = Capability {
            id: "test".into(),
            description: "Test cap".into(),
            min_ring: 1,
            scope: "dev".into(),
        };
        let dict = serde_json::to_value(&c).unwrap();
        assert_eq!(dict["id"], "test");
        assert_eq!(dict["min_ring"], 1);
    }

    #[test]
    fn test_capability_set_has() {
        let caps = CapabilitySet {
            capabilities: vec![
                Capability {
                    id: "read".into(),
                    description: "Read".into(),
                    min_ring: 3,
                    scope: "".into(),
                },
                Capability {
                    id: "write".into(),
                    description: "Write".into(),
                    min_ring: 2,
                    scope: "".into(),
                },
            ],
        };
        assert!(caps.has("read"));
        assert!(caps.has("write"));
        assert!(!caps.has("delete"));
    }

    #[test]
    fn test_capability_set_check() {
        let caps = CapabilitySet {
            capabilities: vec![Capability {
                id: "admin".into(),
                description: "Admin".into(),
                min_ring: 0,
                scope: "".into(),
            }],
        };
        assert!(caps.check("admin", 0));
        assert!(!caps.check("admin", 1));
        assert!(!caps.check("nonexistent", 0));
    }

    #[test]
    fn test_capability_set_by_scope() {
        let caps = CapabilitySet {
            capabilities: vec![
                Capability {
                    id: "c1".into(),
                    description: "".into(),
                    min_ring: 0,
                    scope: "system.admin".into(),
                },
                Capability {
                    id: "c2".into(),
                    description: "".into(),
                    min_ring: 1,
                    scope: "system.read".into(),
                },
                Capability {
                    id: "c3".into(),
                    description: "".into(),
                    min_ring: 2,
                    scope: "app.view".into(),
                },
            ],
        };
        let system = caps.by_scope("system");
        assert_eq!(system.capabilities.len(), 2);
        assert!(system.has("c1"));
        assert!(system.has("c2"));
        assert!(!system.has("c3"));

        let app = caps.by_scope("app");
        assert_eq!(app.capabilities.len(), 1);
        assert!(app.has("c3"));
    }

    #[test]
    fn test_capability_set_merge() {
        let a = CapabilitySet {
            capabilities: vec![Capability {
                id: "shared".into(),
                description: "A's version".into(),
                min_ring: 0,
                scope: "".into(),
            }],
        };
        let b = CapabilitySet {
            capabilities: vec![
                Capability {
                    id: "shared".into(),
                    description: "B's version (keeps first)".into(),
                    min_ring: 1,
                    scope: "".into(),
                },
                Capability {
                    id: "unique".into(),
                    description: "Only in B".into(),
                    min_ring: 2,
                    scope: "".into(),
                },
            ],
        };
        let merged = a.merge(&b);
        // Keeps first occurrence of "shared"
        assert_eq!(merged.capabilities.len(), 2);
        assert_eq!(
            merged.capabilities[0].description,
            "A's version"
        );
        assert_eq!(
            merged.capabilities[1].description,
            "Only in B"
        );
    }

    #[test]
    fn test_security_context_can() {
        let caps = CapabilitySet {
            capabilities: vec![Capability {
                id: "admin".into(),
                description: "Admin".into(),
                min_ring: 0,
                scope: "".into(),
            }],
        };
        let ctx = SecurityContext {
            ring: 0,
            capabilities: caps,
            sandboxed: false,
        };
        assert!(ctx.can("admin"));
        assert!(!ctx.can("nonexistent"));
    }

    #[test]
    fn test_security_context_user_ring() {
        let caps = CapabilitySet {
            capabilities: vec![
                Capability {
                    id: "admin".into(),
                    description: "Admin".into(),
                    min_ring: 0,
                    scope: "".into(),
                },
                Capability {
                    id: "read".into(),
                    description: "Read".into(),
                    min_ring: 3,
                    scope: "".into(),
                },
            ],
        };
        let ctx = SecurityContext {
            ring: 3,
            capabilities: caps,
            sandboxed: true,
        };
        assert!(ctx.can("read"));
        assert!(!ctx.can("admin")); // Kernel-only
    }

    #[test]
    fn test_build_surface_no_context() {
        // Cannot call build_pgg_archon_security_policy_surface without Python runtime
        // Just verify the context-None branch logic
        let surface = build_surface_inner(None);
        assert_eq!(surface.status, "WATCH");
        assert!(surface.warnings.contains(&"SecurityContextMissing".to_string()));
    }

    #[test]
    fn test_build_surface_kernel_not_sandboxed() {
        let surface = build_surface_inner(Some(ContextInput {
            ring: 0,
            sandboxed: false,
            capabilities: vec![],
        }));
        assert_eq!(surface.status, "PASS");
        assert_eq!(surface.ring, Some(0));
        assert_eq!(surface.ring_name, "Kernel");
    }

    #[test]
    fn test_build_surface_user_sandboxed() {
        let surface = build_surface_inner(Some(ContextInput {
            ring: 3,
            sandboxed: true,
            capabilities: vec![],
        }));
        assert_eq!(surface.status, "PASS");
        assert_eq!(surface.ring, Some(3));
        assert_eq!(surface.ring_name, "User");
    }

    #[test]
    fn test_build_surface_unusual_context() {
        let surface = build_surface_inner(Some(ContextInput {
            ring: 1,
            sandboxed: true,
            capabilities: vec![],
        }));
        assert_eq!(surface.status, "WATCH");
        assert_eq!(surface.ring, Some(1));
        assert_eq!(surface.ring_name, "Hypervisor");
        assert!(surface.warnings[0].contains("UnusualSecurityContext"));
    }

    #[test]
    fn test_build_surface_with_capabilities() {
        let surface = build_surface_inner(Some(ContextInput {
            ring: 3,
            sandboxed: true,
            capabilities: vec![CapabilityInput {
                id: "read".into(),
                description: "Read only".into(),
                min_ring: 3,
                scope: "data".into(),
            }],
        }));
        assert_eq!(surface.status, "PASS");
        assert_eq!(surface.capability_count, 1);
    }

    #[test]
    fn test_empty_capability_set() {
        let cs = CapabilitySet {
            capabilities: vec![],
        };
        assert_eq!(cs.capabilities.len(), 0);
        assert!(!cs.has("anything"));
        assert!(!cs.check("anything", 0));
    }

    #[test]
    fn test_timestamp_format() {
        let ts = format_timestamp(0);
        assert_eq!(ts, "1970-01-01T00:00:00+0000");
        let ts2 = format_timestamp(86400);
        assert_eq!(ts2, "1970-01-02T00:00:00+0000");
    }

    // ─── Helper: Rust-only surface builder (no Python) ───

    struct ContextInput {
        ring: i32,
        sandboxed: bool,
        capabilities: Vec<CapabilityInput>,
    }

    struct CapabilityInput {
        id: String,
        description: String,
        min_ring: i32,
        scope: String,
    }

    struct SurfaceOutput {
        status: String,
        ring: Option<i32>,
        ring_name: String,
        capability_count: usize,
        warnings: Vec<String>,
    }

    fn build_surface_inner(context: Option<ContextInput>) -> SurfaceOutput {
        let context = match context {
            Some(ctx) => ctx,
            None => {
                return SurfaceOutput {
                    status: "WATCH".into(),
                    ring: None,
                    ring_name: "Unknown".into(),
                    capability_count: 0,
                    warnings: vec!["SecurityContextMissing".into()],
                };
            }
        };

        let capabilities: Vec<Capability> = context
            .capabilities
            .into_iter()
            .map(|c| Capability {
                id: c.id,
                description: c.description,
                min_ring: c.min_ring,
                scope: c.scope,
            })
            .collect();

        let (status, warnings) = if context.ring == 0 && !context.sandboxed {
            ("PASS".into(), vec![])
        } else if context.ring == 3 && context.sandboxed {
            ("PASS".into(), vec![])
        } else {
            (
                "WATCH".into(),
                vec![format!(
                    "UnusualSecurityContext:ring={} sandboxed={}",
                    context.ring, context.sandboxed
                )],
            )
        };

        SurfaceOutput {
            status,
            ring: Some(context.ring),
            ring_name: ring_name(context.ring),
            capability_count: capabilities.len(),
            warnings,
        }
    }
}

// ─── Module registration ───

#[pymodule]
fn hermes_pgg_security_policy_surface(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("SURFACE_VERSION", SURFACE_VERSION)?;
    m.add("SURFACE_SOURCE", SURFACE_SOURCE)?;
    m.add_class::<PySecurityRing>()?;
    m.add_class::<Capability>()?;
    m.add_class::<CapabilitySet>()?;
    m.add_class::<SecurityContext>()?;
    m.add_function(wrap_pyfunction!(build_pgg_archon_security_policy_surface, m)?)?;
    Ok(())
}