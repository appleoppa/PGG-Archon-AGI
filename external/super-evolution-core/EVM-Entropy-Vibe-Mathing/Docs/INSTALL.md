# EVM 安装部署教程

## 环境依赖

- Python 3.8+
- Node.js 16+ (用于Claw引擎)
- Rust (可选，用于高性能模块)

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/ApexSpiral/EVM-Entropy-Vibe-Mathing.git
cd EVM-Entropy-Vibe-Mathing
```

### 2. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 3. 安装Node.js依赖（可选）

```bash
cd ClawEngine
npm install
cd ..
```

### 4. 配置EVM

```bash
cp Config/evm.config.yaml.example Config/evm.config.yaml
# 编辑 evm.config.yaml 进行自定义配置
```

### 5. 启动EVM引擎

```bash
python CoreFormula/EVM_FORMULA.py
```

## 古法配置加载

在 `evm.config.yaml` 中启用古法赋能:

```yaml
AncientTaoPower:
  TaoTeChing: true   # 道德经
  IChing: true       # 易经
  HuangDiNeiJing: true
  HeTuLuoShu: true
  GanZhiCycle: true
  WuXingBalance: true
  BaGuaPartition: true
```

## 验证安装

```bash
python -c "from CoreFormula.EVM_FORMULA import EVMCore; e = EVMCore(); print(e.calculate_evm())"
```

预期输出: `0.6856` (或接近值)
