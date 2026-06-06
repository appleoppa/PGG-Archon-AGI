# Local runtime truthfulness for AGI/PGG deployment tasks

When the user asks to continue an AGI/PGG/APEX deployment until “all unfinished items” are complete, apply this truth gate:

## State labels

1. **UI-only online**: browser/dashboard responds, but Rust/runtime or provider path is not proven.
2. **Runtime online**: a compiled local runtime process serves health and chat endpoints.
3. **Root crate deployable**: root Rust crate passes `cargo check --all-targets`, `cargo test --all-targets`, `cargo build --release`, and the release binary is the running service.
4. **Provider-backed interaction**: runtime chat endpoint calls a real configured LLM provider and returns a response whose mode/evidence identifies the provider path.
5. **Full generated core integrated**: experimental/generated cognitive modules are linked into the deployable crate and have semantic tests. This is much stronger than state 3.

## Required wording

- If state 4 is reached but state 5 is not, say: “可运行部署 + 真实 LLM 交互链路完成；生成核心模块仍作为保留资产，未宣称完整 AGI。”
- Never collapse state 3/4 into state 5.
- If the user asks to continue, move from the lowest unproven state upward and verify each step with external evidence before summarizing.

## Evidence checklist

- Process/port evidence for runtime and Web UI.
- Direct runtime `/api/health` and `/api/chat` response.
- Web UI proxy `/api/chat` response.
- Build/test outputs for root crate.
- Git remote verification if the task includes saving to GitHub.
- PGG runtime loop evidence: module status, debate, ECC, SQLite persistence when the task is AGI/PGG/evolution class.
