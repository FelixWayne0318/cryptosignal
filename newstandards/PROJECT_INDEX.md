# PROJECT_INDEX.md
版本：v2.0 · 作用：**文档导航 + 最小使用路径**（避免与系统默认 `README.md` 冲突）

> 本仓库（`newstandards/`）是 CryptoSignal v6 的**口径与运行规范**集合。  
> 目标：**A 层方向证据** → **B 层环境调节（F/I）** → **C 层执行/流动性** → **D 层概率/EV→离散发布**，并提供**新币专用通道**与**稳定数据底座**。

---

## 1) 快速上手（不写代码的最小路径）
按下列顺序阅读即可把系统跑通（口径层面）：
1. **`STANDARDS.md`**：总原则 + 因子统一标准化链（EW-Median/MAD → 软 winsor → tanh 到 ±100）、聚合与执行规则  
2. **`MODULATORS.md`**：F/I 只调 **Teff / cost_eff / 发布门槛**，不碰方向分；分段奖惩，防“负负得正”  
3. **`PUBLISHING.md`**：分边概率、校准/收缩、EV 计算、Prime 发布（滞回/持久/冷却）  
4. **`DATA_LAYER.md`**：数据 SLO、**3–5 路组合流**拓扑、快照对账、DataQual 与缓存/持久化  
5. **`NEWCOIN_SPEC.md`**：USDT-M 新币通道：点火→成势→衰竭的非线性联立，执行更严  
6. **`SCHEMAS.md`**：数据/表结构契约（字段、单位、主键、分区），保证可回放与可验证

**执行侧四道硬闸（任何 Prime 上线前必须通过）**  
`impact ≤ 7–10bps` · `spread ≤ 35bps` · `|OBI| ≤ 0.30` · `DataQual ≥ 0.90`  
不过闸 → **不发 Prime**（仅发布 Watch）。

**发布层防抖三件套**  
`K/N 持久`（如 2/3 根确认） + `门槛滞回`（发布阈高、维持阈低） + `降级冷却 60–120s`。

---

## 2) 文档地图（当前已存在的 6 份）
- **[`STANDARDS.md`](./STANDARDS.md)**  
  原则与口径总纲；A 层标准化链；权重与聚合；C 层执行（厚区/impact/OBI、SL/TP）；D 层概率→EV。
- **[`MODULATORS.md`](./MODULATORS.md)**  
  F/I 的数学定义与护栏：只改温度/成本/门槛；分段惩罚/奖励，避免“负负得正”。
- **[`PUBLISHING.md`](./PUBLISHING.md)**  
  分边概率、短样本收缩、EV 计算；Prime 发布的滞回/持久/冷却；强度展示口径。
- **[`DATA_LAYER.md`](./DATA_LAYER.md)**  
  数据 SLO；**3–5 路** WS 组合流；簿面快照+增量对账；DataQual；缓存与持久化契约。
- **[`NEWCOIN_SPEC.md`](./NEWCOIN_SPEC.md)**  
  新币进入/回切；分钟级点火→成势→衰竭条件；更严的执行闸门与概率收缩；TTL/并发。
- **[`SCHEMAS.md`](./SCHEMAS.md)**  
  原始层/特征层/决策层的表结构、字段单位与主键分区；质量与对账状态表；强一致性校验。

> 上述 6 份 = **可运行的口径标准**。实现层须严格遵循其**单位/范围/阈值**与**数据契约**。

---

## 3) 目录建议（文档层）

newstandards/
├─ PROJECT_INDEX.md           ← 本文件（入口/索引）
├─ STANDARDS.md
├─ MODULATORS.md
├─ PUBLISHING.md
├─ DATA_LAYER.md
├─ NEWCOIN_SPEC.md
└─ SCHEMAS.md

---

## 4) 版本与变更
- 当前规范：**v2.0**（多空对称、A/B/C/D 解耦；F/I 只调三件事；发布离散但防抖）。  
- 变更纪律：任何影响口径/单位/阈值的修改，**先影子跑**（rank-corr ≥ 0.90）再灰度；在 `CHANGELOG.md` 记录**变更项/理由/预期影响/回滚条件**。

---

## 5) 合规与范围
- 仅使用 Binance **公开端点**（REST/WS）；未接入私有写权限则**不触发交易**。  
- 如后续接入下单/持仓，密钥仅走环境变量，容器只读文件系统，并遵循地区合规。

---

### 一句话
这 **6 份规范 + 本索引** 已形成**口径闭环**：看得懂 → 拉得起 → 跑得稳 → 可评测 → 可回滚。  
需要评测与上线流程文档时，再补 `EVAL_MANUAL.md / RUNBOOK.md / ALERTS_PLAYBOOK.md` 等增强件。