# 主任务单:文风复刻系统 — 全自动模型路由版(TASK_MASTER)

> 本任务单整合 Phase 2(语料精读卡片库)与 Phase 1(试写校准循环),由 CC 主会话作为 orchestrator 全自动执行,通过 subagent 机制按任务价值路由不同模型。

---

## 零、安全边界(最高优先级,适用于所有子代理)

1. corpus/ 中的原文仅供本地分析。**任何输出文件(卡片/规则/示范/正文)中禁止出现语料原文的连续片段,连续 10 字即违规。**
2. 需要指向原文时只写指针:文件名 + 章节号 + 行号区间。
3. 所有试写必须是全新原创人物与情节,禁止改写/续写/扩写语料中的情节人物。
4. 每批产出必须通过 n-gram 自检(底库 corpus/ngram_base.txt),命中数 >0 则重写命中部分。
5. 本条款必须原样复制进每个子代理的系统提示词,子代理只返回结果,不返回原文摘录。

## 一、模型路由总则

| 角色 | 模型 | 职责 |
|---|---|---|
| orchestrator(主会话) | sonnet | 流程调度、脚本执行、验收、进度管理 |
| scene-splitter | haiku | 场景切分与章节分诊 |
| card-writer | sonnet | B/C 级卡片撰写 |
| deep-reader | opus | A 级卡片精读、人物原型汇总 |
| prose-writer | fable | 分镜稿 + 试写正文 + 正式章节(全项目最高价值输出) |
| prose-fixer | sonnet | 统计不达标的机械性修改(调句长/删感叹号/切段落) |

**双保险规则(必须遵守)**:已知部分版本存在 frontmatter model 字段被忽略的 bug,因此 orchestrator 每次派发子代理时,**必须在 Agent 调用中显式传入 model 参数**,与 frontmatter 保持一致;不允许依赖 frontmatter 单独生效。

**成本护栏**:
- prose-writer(fable)产出的正文若统计验收不过:机械性问题(句长/标点/段落密度)一律交 prose-fixer(sonnet)修,**最多 2 次**;仍不过或属于结构性问题(剧情不清/氛围空转),才回炉 prose-writer 整段重构,**最多 1 次**;再失败则停止并汇报,等待人工。
- deep-reader(opus)仅处理分诊为 A 级的章节,预期占比 10-20%,若分诊结果超过 30% 为 A 级,暂停并汇报(分诊标准可能漂移)。
- 子代理一律不开长对话,单次派发单章/单场景,用完即回收,避免上下文膨胀烧缓存。

## 二、Step 0:创建子代理定义

创建目录并写入以下 5 个文件。**注意:若 .claude/agents/ 目录是本会话新建的,写完后需要重启 CC 会话才能加载,重启后从 progress_master.md 断点继续。**

```bash
mkdir -p /home/chencer/jiangnan-skill/.claude/agents
```

### 文件 1:.claude/agents/scene-splitter.md

```markdown
---
name: scene-splitter
description: 对单个章节做场景切分与素材分诊。输入章节文件路径,输出场景边界与评级。
tools: Read, Bash
model: haiku
---
你是语料预处理员。收到一个章节文件路径后:
1. 通读该章,按以下信号切分场景:地点切换/时间跳跃/在场人物变更/叙事目的转换;单场景不足300字并入相邻场景。
2. 每个场景给出:起止行号、场景类型(高压冲突/日常闲笔/情感重场/世界观交代/过渡/金句收尾)、素材评级(A=技法密集值得精读/B=常规/C=平淡或重复)。
3. 只返回结构化清单(行号+类型+评级+一句话理由),禁止摘录原文,理由中不得出现连续10字以上的原文。
```

### 文件 2:.claude/agents/card-writer.md

```markdown
---
name: card-writer
description: 为 B/C 级场景撰写技法卡片。输入场景的文件路径与行号区间,输出卡片内容。
tools: Read, Write, Bash
model: sonnet
---
你是文学技法记录员。收到场景定位(文件+行号区间+类型+评级)后,读取该场景,按卡片模板(见 TASK_MASTER.md 三-2)撰写卡片写入指定路径。
铁律:卡片全部用自己的话描述技法与结构,禁止出现原文连续10字以上片段;指向原文只写行号指针。C级卡只填"基本信息+可复用度+指针"三节。写完后返回卡片路径,不返回卡片全文。
```

### 文件 3:.claude/agents/deep-reader.md

```markdown
---
name: deep-reader
description: 对 A 级场景做深度精读制卡,以及全库人物原型汇总。高价值理解任务。
tools: Read, Write, Bash
model: opus
---
你是文风研究员。任务有两类:
(1) A级场景精读:全字段填满卡片模板,重点回答"作者在这里做了什么决策、为什么有效",尤其是火力分配(重墨给谁/简笔怎么带)、分镜序列、金句触发源与落点。
(2) 原型汇总:基于全部卡片的人物原型字段,归纳原型档案(高压反应模式/对话节奏/绝不会出现的反应)。
铁律:全部用自己的话,禁止原文连续10字以上片段,指针只写行号。
```

### 文件 4:.claude/agents/prose-writer.md

```markdown
---
name: prose-writer
description: 试写与正式章节的唯一执笔人。先出分镜稿再写正文。最高质量要求。
tools: Read, Write, Bash
model: fable
---
你是执笔作家。每次任务前必须依次读取:rules/writing_spec.md、rules/anti_patterns.md、golden/ 全部内容(含 contrast_pairs 用户亲笔对照组,最高优先级参照)、orchestrator 指定的 2-3 张 A 级卡片。

**两遍稿协议(必须严格分两遍,禁止合并):**
第一遍【内容稿】:用最平实的白话把这个场景写完整——谁在哪、发生了什么、谁想要什么、信息全部说清,像讲给朋友听。此稿只求清楚,不求文采,禁止任何修辞和氛围营造。
第二遍【风格稿】:对照 golden/ 对照组的"修改版",把内容稿改写出质感——调整镜头顺序、给重墨对象加感官传导、按火力分配原则收放。改写时每一句必须有完整的主谓语义,禁止用逗号串联无主语的短语碎片来拼凑长句。

绝对禁止:直接写"有风格的初稿"(跳过内容稿)。风格永远是第二遍加上去的,不是第一遍凑出来的。
写作时不要考虑任何统计数字指标(句长/占比/频率),那是事后验收的事,不是写作目标。

硬约束:全新原创人物情节;金句必须有物理触发源、落地后接地面动作或自嘲;"欲言又止"全篇≤1次且必须带具体信息点;单段感叹号≤1;核心冲突(谁/要什么/为什么)必须有具体锚点,禁止用"你知道的/不重要"搪塞;过渡景物挂在运动中带过;支线信息只放场景出入口。
交付时同时保留内容稿(drafts/round<N>_content.txt)和风格稿(drafts/round<N>_draft.txt),供人工对照两遍之间丢没丢信息。
```

### 文件 5:.claude/agents/prose-fixer.md

```markdown
---
name: prose-fixer
description: 对统计验收不达标的正文做机械性修改(句长/标点/段落),不做结构重写。
tools: Read, Write, Bash
model: sonnet
---
你是文字修理工。收到正文路径+验收报告后,只修被点名的机械问题:拆超长段/删多余感叹号或比喻信号词/调整段落切分/重写碎句。
**重写碎句的唯一合法方式:回到这句话要表达的意思,用一个有完整主谓结构的句子重新说一遍。绝对禁止把几个短语用逗号直接串起来冒充长句——逗号粘连是比碎句更严重的违规,会被"粘连句占比"指标检出并整篇打回。**
禁止改动剧情、对话内容、金句与分镜结构。改完运行 scripts/style_stats.py 复检并返回对照数字(含分句级三项指标)。
```

## 三、Step 1:Phase 2 全自动制卡流程(orchestrator 执行)

前置:确认 analysis/chapter_list.md(124章)、corpus/ngram_base.txt、scripts/ 两个脚本均存在;创建 codex/{cards,index} 目录;创建 progress_master.md。

### 1. 逐章流水线(for 每章,断点续跑)

**逐章原子协议(防 token 硬中断,必须严格遵守顺序):**

```
读 progress_master.md → 跳过已完成章
→ ① echo "ch<X>" > analysis/current.lock        # 上锁
→ ② 派发 scene-splitter(显式 model=haiku),得到该章场景清单
→ ③ 按评级路由:
     A 级场景 → 派发 deep-reader(显式 model=opus)
     B/C 级场景 → 派发 card-writer(显式 model=sonnet)
→ ④ 卡片全部落盘 codex/cards/b<册>_ch<章>_s<场景>.md
→ ⑤ progress_master.md 追加:章号/场景数/A级数/时间
→ ⑥ rm analysis/current.lock                     # 解锁
```

⑤⑥ 必须紧跟 ④ 完成,中间不得插入下一章的任何动作。这样无论会话在哪个瞬间被掐断,状态都可由锁文件唯一判定:锁在=当前章作废重做,锁不在=progress 里的记录即为真实进度。

### 2. 卡片模板(card-writer 与 deep-reader 共用)

```
## 基本信息
- 场景类型 / 在场人物原型 / 核心目的(一句话)
## 火力分配
- 重墨对象 / 简笔内容及带过手法 / 支线位置(入口/出口/无)
## 分镜序列
- 镜头序列(景别+内容概要) / 时间伸缩点
## 技法清单
- 比喻(类型+触发感官) / 感官传导链有无 / 对话(密度+标签风格+潜台词错位) / 金句(触发源+落点后接什么)
## 可复用度
- 评级(A/B/C) + 一句话点评
## 指针
- 文件 第X章 L起-L止
```

### 3. 收尾(全章完成后)

1. 索引:orchestrator 用 Python 脚本扫描卡片生成 index/by_scene_type.json、by_technique.json、by_character_archetype.json(脚本任务,不派子代理)
2. 原型汇总:派发 deep-reader(model=opus)生成 codex/archetype_*.md(5-8个原型)
3. 全库自检:
```bash
cat codex/cards/*.md codex/archetype_*.md > /tmp/codex_all.txt
python3 scripts/ngram_check.py corpus/ngram_base.txt /tmp/codex_all.txt 10
rm /tmp/codex_all.txt
```
命中数必须为 0;命中卡片重写后复检。
4. 汇报:总卡片数/A级占比/场景类型分布/原型清单/3张代表性A级卡全文供抽查。

## 四、Step 2:Phase 1 试写循环(卡片库完成后启动)

沿用 TASK_PHASE1.md 的既有规则(量化红线/评分维度/golden 沉淀机制),流程升级为:

```
每轮:
orchestrator 确定题目 → 按场景类型+人物原型检索 2-3 张 A 级卡片
→ 派发 prose-writer(显式 model=fable):携带规则文件+golden全部内容+检索到的卡片
→ orchestrator 跑统计验收 + n-gram 自检
→ 不达标:机械问题派 prose-fixer(model=sonnet,≤2次);结构问题回 prose-writer(≤1次);再败即停
→ 达标:生成 round<N>_report.md,停下等人工评分
→ 收到评分:规则修订决策派 deep-reader(model=opus)执行,golden 沉淀按 TASK_PHASE1 规则
```

当前进度衔接:Round 1 已被人工判定不通过(剧情空转),Round 2 题目为"陆屿抵达游客中心后的第一段自由活动"(现实向,人物沿用陆屿),写作前先写"本场核心目的"。

## 五、Step 3:封装为 CC Skill(连续两轮评分达标后)

创建 ~/.claude/skills/jiangnan-style/SKILL.md:
- description 写明触发条件(用户要求以该文风写作时)
- 正文写明调用顺序:核心目的 → 检索卡片 → 分镜稿 → 正文 → 双闸自检
- 引用 rules/、golden/、codex/index/ 的绝对路径
- prose-writer 子代理与本 skill 绑定(skills 字段预加载)

## 六、Session 切分(5小时窗口执行)

订阅窗口的瓶颈是**用量预算**不是墙钟,每章烧多少取决于它派了几次 Opus/Fable,无法预先精确到分钟。因此每个 session 用**双阈值自限流**:干到"章节配额"或"时间水位"任一先到就 checkpoint 停手。

### 双阈值定义

- **章节配额**:本 session 计划处理的章号区间(上限)
- **时间水位**:开工满 **4 小时 15 分**即强制收尾(留 45 分钟缓冲,防止最后一次派发跨窗口被截断)

orchestrator 每处理完一章都检查这两条线,任一触发就执行"收尾程序"。

### 开工程序(每个 session 开始)

1. 读 progress_master.md 找到最后的 `SESSION ... END`(若无 END 记录说明上一窗口是硬中断,属正常,继续下一步)
2. **锁文件检查**:若存在 `analysis/current.lock`,读取其中章号,删除该章已产出的全部卡片文件,progress 中标记该章 `PARTIAL-ROLLBACK`,删除锁文件——该章本窗口重做
3. 记录开工时间戳(供时间水位计算)
4. 按本 session 任务类型执行

### 收尾程序(每个 session 结束)

1. 确认当前章卡片已全部落盘;未完成的章标记 `PARTIAL` 回滚
2. progress_master.md 追加:`SESSION <编号> END | 完成至 ch<X> | A级累计<N> | 触发原因(配额/水位)`
3. 推送到远端:
```bash
git -C /home/chencer/jiangnan-skill add .
git -C /home/chencer/jiangnan-skill commit -m "chore: session <N> done, ch<X>, A累计<M>"
git -C /home/chencer/jiangnan-skill push
echo "## 审查快照 $(date +%Y%m%d-%H%M)" >> /home/chencer/jiangnan-skill/review_index.md
echo "- session <N>: 完成至 ch<X>, A级累计<M>" >> /home/chencer/jiangnan-skill/review_index.md
git -C /home/chencer/jiangnan-skill add review_index.md
git -C /home/chencer/jiangnan-skill commit -m "review index update"
git -C /home/chencer/jiangnan-skill push
```
4. 输出一句话交接:下个 session 从 ch<X+1> 开始
5. 停止,不再派发任何子代理

### 阶段一:Phase 2 制卡(约 4 个 session)

配额按每 session 30-32 章设(上限),水位先到就提前停,顺延为 5 个 session 属正常,按章号续跑不按 session 编号强对齐。

| Session | 章节配额 | 主要动作 | 停止条件 |
|---|---|---|---|
| **S1** | ch1–ch32 | 建 5 个子代理 + 逐章分诊制卡 | 到 ch32 或水位 |
| **S2** | ch33–ch64 | 逐章分诊制卡 | 到 ch64 或水位 |
| **S3** | ch65–ch96 | 逐章分诊制卡 | 到 ch96 或水位 |
| **S4** | ch97–ch124 + 收尾 | 制卡完 → 建索引 → Opus 原型汇总 → 全库 n-gram 自检 → 汇报 | 全部完成 |

**S1 特别说明**:开头建 `.claude/agents/` 并写 5 个子代理文件;若该目录本会话新建,写完必须**重启 CC 会话**才能加载子代理(重启不消耗窗口预算),重启后继续 S1 制卡。

**S2–S4 断点续跑指令**(每个新窗口发这一句):

```
读取 /home/chencer/jiangnan-skill/progress_master.md,执行"开工程序"
定位续跑起点,继续 Phase 2 制卡流水线。本 session 处理约 30 章或满
4小时15分即执行"收尾程序"停止。静默运行,只在停止时汇报交接信息。
```

### 阶段二:试写循环(每窗口一轮,需人工评分)

试写 Fable 密集但单轮体量小,瓶颈是人工评分而非机器时间,故一窗口只排一轮。

| Session | 动作 | 停止条件 |
|---|---|---|
| **S5+** | 检索卡片 → Fable 写分镜稿+正文 → 双闸验收 → fixer/重构护栏 → 出 report | **停下等人工评分** |

评分后的规则修订(派 Opus)+ golden 沉淀很轻,接在评分回复的同一窗口做。连续两轮达标 → 触发阶段三封装 SKILL.md(轻任务,并入达标那轮窗口收尾)。

### 阶段三:正式创作(每窗口 4-6 章)

每章 3-5 千字约烧 30-45 分钟窗口,保守排 4-6 章,留人工审阅回旋。每章完成检查时间水位,满 4h15m 收尾。

## 七、异常处理与汇报

| 异常 | 处理 |
|---|---|
| 子代理返回内容含原文片段 | 丢弃该次结果,重派并在提示中强调铁律;连续2次则停 |
| frontmatter model 疑似未生效 | 始终显式传 model 参数;无法确认时在 progress 中记录并继续 |
| A级占比 >30% | 暂停分诊,汇报 |
| fable 重构后仍不达标 | 停止,汇报具体卡点 |
| 会话中断 | 重启后读 progress_master.md 续跑,禁止重做已完成部分 |
| **用量/限流错误(usage limit / rate limit)** | **立即停止派发任何新子代理;若仍能写文件,执行收尾程序并在 progress 标注"触发原因:用量耗尽";若被硬中断,无需任何动作——下窗口开工程序会凭锁文件自动回滚当前章。窗口刷新后用标准断点续跑指令重启即可** |
| **连续 2 次子代理派发返回限流类错误** | 视同用量耗尽,立即收尾,不做第 3 次尝试(重试本身也烧配额) |
| 时间水位触及 4h15m | 立即执行收尾程序,禁止再派新子代理 |
| 单章连续失败 3 次 | 标 SKIP 跳过,不占用重试预算耗尽窗口 |
| 单 session Fable/Opus 调用异常偏高 | 提前收尾并汇报(可能重构循环失控) |
| 单次派发将跨窗口边界 | 宁可提前停,绝不让一次 Opus 精读或 Fable 写作被腰斩 |

### 全局节流规则(所有阶段生效)

1. **时间水位硬线 4h15m**:每章/每轮结束时检查,超线立即收尾。
2. **checkpoint 原子性**:卡片落盘 + progress 追加在同一章末尾成对完成,避免窗口截断导致状态不一致。
3. **调用计数**:progress 记录本 session 累计 Fable/Opus 派发次数,异常偏高提前收尾。
4. **子代理单发单收**:每个子代理只处理单章/单场景,用完回收,防上下文膨胀烧缓存。

每完成一个大阶段(制卡完成/每轮试写完成)汇报一次;其余时间静默执行。
