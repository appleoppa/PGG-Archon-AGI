# 贡献指南 CONTRIBUTING

感谢您对盘古的兴趣！欢迎贡献代码。

---

## 开发环境

```bash
# 克隆仓库
git clone https://github.com/ApexSpiral/LLM-Pangu.git
cd LLM-Pangu

# 安装依赖
bash install.sh

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate
pip install pytest pyyaml
```

---

## 开发规范

### Python代码规范

- 使用 **snake_case** 命名函数和变量
- 使用 **PascalCase** 命名类
- 使用 **UPPER_SNAKE_CASE** 命名常量
- 必须包含 **docstring**（使用Google风格）
- 单行不超过 **120字符**

### 提交规范

```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式（不影响功能）
refactor: 重构
test: 测试相关
chore: 构建/工具
```

### 分支管理

- `main` - 主分支，稳定版本
- `develop` - 开发分支
- `feature/*` - 功能分支
- `fix/*` - 修复分支

---

## 测试

```bash
# 运行所有测试
python3 -m pytest tests/ -v

# 运行单个测试文件
python3 -m pytest tests/test_pangu.py::TestShannonEntropy -v

# 带覆盖率
python3 -m pytest tests/ --cov=. --cov-report=html
```

---

## Pull Request流程

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: 添加某功能'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 问题反馈

请通过 GitHub Issues 反馈问题。

---

感谢您的贡献！
