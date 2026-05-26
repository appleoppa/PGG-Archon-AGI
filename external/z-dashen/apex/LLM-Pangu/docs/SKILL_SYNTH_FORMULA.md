# SkillSynth 核心公式

## LaTeX源码（可直接复制到Overleaf）

```latex
\documentclass{article}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{mathtools}

\begin{document}

\title{SkillSynth 核心公式}
\author{ApexSpiral}

\section{核心范式}

\subsection{任务合成通过率}

\[
P_{\text{task}} = \frac{N_{\text{usable}}}{N_{\text{path}}} \times 100\% = \frac{3560}{3721} \approx \mathbf{95.7\%}
\]

\subsection{模型参数量倍率}

\[
R_{\text{size}} = \frac{480\text{B}}{32\text{B}} = \mathbf{15}
\]

\subsection{性能提升（Terminal-Bench 1.0）}

\[
\Delta_{1.0} = 33.8\% - 23.9\% = \mathbf{+9.9\%}
\]

\subsection{性能差距（Terminal-Bench 2.0）}

\[
\Delta_{2.0} = 39.6\% - 29.6\% = \mathbf{-10\%}
\]

\subsection{场景-技能图规模}

\[
\text{Nodes} = 82073,\quad \text{Edges} = 185529,\quad \text{Skills} = 57214
\]

\subsection{平均修复轮次}

\[
\bar{R} = \mathbf{2.3}
\]

\subsection{单任务成本}

\[
C_{\text{task}} = \mathbf{\$27.3}
\]

\subsection{核心范式（APEX 公式化）}

\[
\text{SkillSynth} = \text{Graph} \xrightarrow{\text{采样}} \text{Sample} \xrightarrow{\text{实例化}} \text{Instantiate}
\]

\[
\text{Trajectory} \propto \text{Path}_{\text{Graph}}
\]

\section{变量定义}

\begin{itemize}
    \item $P_{\text{task}}$: 任务合成通过率
    \item $N_{\text{usable}}$: 可用路径数 (3560)
    \item $N_{\text{path}}$: 总路径数 (3721)
    \item $R_{\text{size}}$: 模型参数量倍率
    \item $\Delta_{1.0}$: Terminal-Bench 1.0性能提升
    \item $\Delta_{2.0}$: Terminal-Bench 2.0性能差距
    \item $\bar{R}$: 平均修复轮次
    \item $C_{\text{task}}$: 单任务成本
\end{itemize}

\end{document}
```

---

## 公式速查表

| 公式 | 值 |
|------|-----|
| $P_{\text{task}}$ | 95.7% |
| $R_{\text{size}}$ | 15 |
| $\Delta_{1.0}$ | +9.9% |
| $\Delta_{2.0}$ | -10% |
| Nodes | 82073 |
| Edges | 185529 |
| Skills | 57214 |
| $\bar{R}$ | 2.3 |
| $C_{\text{task}}$ | \$27.3 |

---

## 核心范式

```
SkillSynth = Graph → Sample → Instantiate
Trajectory ∝ Path_Graph
```
