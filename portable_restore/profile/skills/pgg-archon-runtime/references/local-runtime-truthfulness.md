# PGG/AGI Local Runtime Truthfulness Pattern

Use when the user asks to "吞噬", "开启 AGI 之路", or complete local deployment of an AGI/APEX/PGG-style repository.

## Key lesson

The user expects active execution, but also correctness. Do not stop at a plan or a Web UI shell. Convert the material into a verifiable local runtime while preserving truthful boundaries.

## Minimum acceptable local runtime evidence

1. A real compiled/runtime process exists.
2. It exposes a health endpoint with service/version/status.
3. It exposes an interaction endpoint, even if initially a placeholder adapter.
4. Web UI or user-facing entry is wired to that runtime, not just a separate dashboard.
5. Build/test evidence exists:
   - `cargo check --all-targets` pass for Rust work when applicable.
   - `cargo test --all-targets` pass or a clearly scoped failure list.
   - release build pass when claiming deployability.
6. The result is pushed only after local verification passes.

## Truthful boundary language

Say:

- "可运行部署面完成"
- "root crate 已可编译/测试/运行"
- "Web UI 已转发到 Rust runtime"
- "实验性源码资产已保留但未全部链接"

Do not say:

- "完整 AGI 自主认知已完成"
- "全部生成模块都已运行"
- "吞噬完成" without build/test/runtime evidence.

## Workflow

1. Run status/debate/ECC if the task is AGI/PGG architecture-sensitive.
2. Identify the smallest honest runtime surface.
3. Compile and test that surface.
4. Start services locally and curl endpoints.
5. Commit/push only after verification.
6. Report entry URLs and exact limitations.
