"""Tests for PGG Archon Security Policy Surface."""

from __future__ import annotations

from agent.pgg_archon_security_policy_surface import (
    SURFACE_SOURCE,
    SURFACE_VERSION,
    Capability,
    CapabilitySet,
    SecurityContext,
    SecurityRing,
    build_pgg_archon_security_policy_surface,
)


def test_kernel_context_no_sandbox():
    """Kernel context (ring=0) with sandboxed=False -> PASS."""
    result = build_pgg_archon_security_policy_surface({
        "ring": 0,
        "sandboxed": False,
        "capabilities": [],
    })
    assert result["schema"] == SURFACE_VERSION
    assert result["source"] == SURFACE_SOURCE
    assert result["status"] == "PASS"
    assert result["ring"] == 0
    assert result["ring_name"] == "Kernel"
    assert result["sandboxed"] is False
    assert result["capability_count"] == 0
    assert result["warnings"] == []
    assert result["agi_completion_claim"] is False


def test_user_context_sandboxed():
    """User context (ring=3) with sandboxed=True -> PASS."""
    result = build_pgg_archon_security_policy_surface({
        "ring": 3,
        "sandboxed": True,
        "capabilities": [],
    })
    assert result["schema"] == SURFACE_VERSION
    assert result["status"] == "PASS"
    assert result["ring"] == 3
    assert result["ring_name"] == "User"
    assert result["sandboxed"] is True
    assert result["warnings"] == []
    assert result["agi_completion_claim"] is False


def test_context_with_capabilities_shows_count():
    """Context with capabilities shows capability count in report."""
    result = build_pgg_archon_security_policy_surface({
        "ring": 2,
        "sandboxed": True,
        "capabilities": [
            {"id": "read_db", "description": "Read database", "min_ring": 2, "scope": "db:read"},
            {"id": "write_db", "description": "Write database", "min_ring": 1, "scope": "db:write"},
            {"id": "admin", "description": "Admin access", "min_ring": 0, "scope": "admin"},
        ],
    })
    assert result["schema"] == SURFACE_VERSION
    assert result["ring"] == 2
    assert result["ring_name"] == "Supervisor"
    assert result["capability_count"] == 3
    assert len(result["capabilities"]) == 3
    assert result["agi_completion_claim"] is False


def test_capability_ring_logic():
    """Test Capability.accessible_by and CapabilitySet.has/check logic."""
    caps = CapabilitySet(capabilities=[
        Capability(id="read", description="Read access", min_ring=3, scope="read"),
        Capability(id="write", description="Write access", min_ring=2, scope="write"),
        Capability(id="admin", description="Admin access", min_ring=0, scope="admin"),
    ])

    # Kernel (ring 0) can access everything
    assert caps.has("read") is True
    assert caps.has("nonexistent") is False
    assert caps.check("read", 0) is True
    assert caps.check("write", 0) is True
    assert caps.check("admin", 0) is True

    # User (ring 3) can access read (min_ring=3) but not write (min_ring=2) or admin (min_ring=0)
    assert caps.check("read", 3) is True
    assert caps.check("write", 3) is False
    assert caps.check("admin", 3) is False

    # Supervisor (ring 2) can access read and write, but not admin
    assert caps.check("read", 2) is True
    assert caps.check("write", 2) is True
    assert caps.check("admin", 2) is False

    # by_scope filtering
    read_caps = caps.by_scope("read")
    assert len(read_caps.capabilities) == 1
    assert read_caps.capabilities[0].id == "read"

    admin_caps = caps.by_scope("admin")
    assert len(admin_caps.capabilities) == 1

    # merge deduplicates
    more_caps = CapabilitySet(capabilities=[
        Capability(id="read", description="Read access dup", min_ring=3, scope="read"),
        Capability(id="execute", description="Execute access", min_ring=1, scope="execute"),
    ])
    merged = caps.merge(more_caps)
    assert len(merged.capabilities) == 4
    assert merged.capabilities[0].id == "read"
    assert merged.capabilities[1].id == "write"
    assert merged.capabilities[2].id == "admin"
    assert merged.capabilities[3].id == "execute"

    # SecurityContext.can
    ctx = SecurityContext(ring=2, capabilities=caps)
    assert ctx.can("read") is True
    assert ctx.can("write") is True
    assert ctx.can("admin") is False
    assert ctx.can("nonexistent") is False


def test_missing_context_returns_watch():
    """None context -> WATCH + SecurityContextMissing."""
    result = build_pgg_archon_security_policy_surface(None)
    assert result["schema"] == SURFACE_VERSION
    assert result["status"] == "WATCH"
    assert result["ring"] is None
    assert result["capability_count"] == 0
    assert result["warnings"] == ["SecurityContextMissing"]
    assert result["agi_completion_claim"] is False
