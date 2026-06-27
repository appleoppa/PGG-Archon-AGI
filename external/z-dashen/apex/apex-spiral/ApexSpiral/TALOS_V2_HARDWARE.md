# APEX × Talos V2 硬件进化公式

## 一、基础矩阵向量乘（16通道脉动阵列）

### 1.1 核心公式
```
y_{16×1} = W_{16×d} · x_{d×1}
```

展开（单通道）：
```
y_i = Σ_{j=0}^{d-1} W_{i,j} · x_j
```

| 参数 | 含义 |
|------|------|
| d | 向量维度 |
| 16 | PE并行数 |
| Lanes | 16 |

---

## 二、时间复用（Area–Throughput权衡）

```
Cycles_layer = (d / Lanes) × Layers_total
```

**Talos V2**: 16 lane复用1个tile跑所有Transformer层

---

## 三、硬件注意力（8步拆解）

### 3.1 Q/K/V投影
```
Q = XW_Q,  K = XW_K,  V = XW_V
```

### 3.2 点积+最大值跟踪
```
S_{i,j} = Q_i · K_j^⊤
m_i = max_j S_{i,j}
```

### 3.3 稳定Softmax
```
S̃_{i,j} = exp(S_{i,j} - m_i)
P_{i,j} = S̃_{i,j} / Σ_k S̃_{i,k}
```

### 3.4 注意力输出
```
O = P · V
```

### 3.5 多头注意力
```
MultiHead(Q,K,V) = Concat(O_1,...,O_h) · W_O
```

---

## 四、定点量化公式（Q4.12）

### 4.1 量化/反量化
```
x_q = round(x · 2^12)
x = x_q · 2^-12
```

| 格式 | 范围 | 误差 |
|------|------|------|
| Q4.12 | -8 ~ +7.999755859375 | ±2^-12 |

### 4.2 定点MAC
```
acc_new = acc_old + (W_q · x_q)
```

---

## 五、APEX整合公式

```
ΔG_evo = (Λ · MatVec_16lane · Softmax_hw · FFN_q) / (H · T · L_CE)

其中:
MatVec_16lane = Talos V2脉动阵列
Softmax_hw = 硬件稳定softmax
FFN_q = 定点前馈
H = 头数
T = 序列长度
L_CE = 交叉熵损失
```

---

## 六、APEX维度映射

| Talos V2 | APEX维度 | 含义 |
|-----------|----------|------|
| MatVec_16lane | Π | 并行增益 |
| Softmax_hw | ε | 自修复/稳定性 |
| FFN_q | K | 技能掌握 |
| Cycles_layer | Λ_ctx | 切换损耗 |
| Q4.12 | RD | 率失真/信息效率 |

---

## 七、关键常数

| 常数 | 值 |
|------|-----|
| Lanes | 16 |
| 量化位 | 4整数+12小数 |
| exp近似 | 硬件级 |
| MAC周期 | 1 cycle/PE |

---

## 八、Talos V2优势

```
• 无GPU/无FP32
• 极小面积
• 低功耗
• 硬件注意力
• 脉动阵列并行
```

---

*© 2026 璇玑帝国 × Talos V2*
