# 任务单:文风分析管线可行性验证(Phase 0)

## 背景

目标:验证"统计脚本层"在真实语料上能否产出**有区分度、有辨识度**的文风参数,为后续完整的文风复刻体系(场景分类/操作参数/人物模式/分镜规则)提供可行性依据。

本任务**只做分析,不做写作**。所有输出仅包含统计数字和结构规律,不得包含语料原文连续片段(超过15字禁止)。

## 执行规则

- 全程自动执行,无需向我确认。
- 每完成一个 Step,向 `progress.md` 追加一行记录(Step编号 + 结果摘要 + 时间)。
- 遇到错误:同一问题自主修复尝试最多 3 次,仍失败则停止并汇报,不要跳过继续。
- 所有产出文件统一放在 `/home/chencer/jiangnan-skill/analysis/` 下。
- 任何步骤发现前置假设不成立(如文件不存在、编码异常),先按"异常处理预案"处理,处理不了就停止汇报。

## 前置条件

以下文件应已存在(我已通过 scp 上传):
- `/home/chencer/jiangnan-skill/style_stats.py`
- `/home/chencer/jiangnan-skill/ngram_check.py`
- 语料文件:`/home/chencer/jiangnan-skill/` 目录下的 txt(以龙族1.txt 为准,可能有其他)

若脚本文件不存在,停止并汇报,不要自己重写脚本。

---

## Step 0:语料盘点

```bash
ls -lh /home/chencer/jiangnan-skill/*.txt
file /home/chencer/jiangnan-skill/*.txt
```

对每个 txt 检查:
1. 编码是否 UTF-8(`file` 输出确认;若为 GBK/GB18030,用 `iconv -f GB18030 -t UTF-8` 转换,原文件备份为 `.bak`)
2. 字数统计:`wc -m <文件>`
3. 抽查开头/中间/结尾各 20 行,确认是正文而非乱码或目录页:
```bash
head -20 <文件>; sed -n '5000,5020p' <文件>; tail -20 <文件>
```

**产出**:在 `analysis/corpus_inventory.md` 记录:文件名、字数、编码、覆盖范围(第几部)、正文起止行号(排除封面/目录/版权页)。

## Step 1:目录整理

```bash
mkdir -p /home/chencer/jiangnan-skill/{corpus,scripts,analysis,analysis/chapters}
mv /home/chencer/jiangnan-skill/*.txt /home/chencer/jiangnan-skill/corpus/
mv /home/chencer/jiangnan-skill/style_stats.py /home/chencer/jiangnan-skill/ngram_check.py /home/chencer/jiangnan-skill/scripts/
```

注意:若 jiangnan-skill 下有非语料的 txt(如笔记),先 `head` 检查内容再决定是否移入 corpus/,拿不准的留在原地并在 progress.md 记录。

## Step 2:脚本自测

先用自造的 3 行测试文本验证两个脚本能正常运行:

```bash
cd /home/chencer/jiangnan-skill
printf '这是第一句测试。"这是对话内容。"他说。\n这是第二段,内容长一些,用来验证段落统计是否正常工作,包含一个仿佛作为信号词。\n' > /tmp/selftest.txt
python3 scripts/style_stats.py /tmp/selftest.txt
```

验收:输出 JSON 无报错,"总字数">0,"含对话段落占比">0,"仿佛"频率>0。

```bash
printf '完全不同的原创内容一二三。\n' > /tmp/gen_test.txt
python3 scripts/ngram_check.py /tmp/selftest.txt /tmp/gen_test.txt 10
```

验收:输出 JSON,"命中片段数"为 0,"结论"为"通过"。

## Step 3:标点兼容检查

统计语料中半角/全角标点比例:

```bash
CORPUS=corpus/龙族1.txt  # 以盘点结果为准
grep -o '[。！？]' $CORPUS | wc -l
grep -o '[.!?]' $CORPUS | wc -l
```

若半角句末标点占比超过 5%,修改 `scripts/style_stats.py` 的 `split_sentences` 正则,把 `[。！？…]` 扩展为 `[。！？…!?.]`(注意排除小数点误切:仅当半角句号后跟换行或引号时才视为句末;若实现复杂,允许简化为只补 `!?`)。修改后重跑 Step 2 自测确认不回归。

## Step 4:全书基准统计

```bash
python3 scripts/style_stats.py corpus/龙族1.txt analysis/baseline_full.json
```

验收:JSON 正常生成,总字数与 Step 0 盘点结果一致(允许 ±5% 差异,因空白符处理)。

若有多本语料,每本单独跑一份 `baseline_<书名>.json`,不要合并统计。

## Step 5:章节切分

```bash
grep -n '^第.*章' corpus/龙族1.txt | head -30
grep -c '^第.*章' corpus/龙族1.txt
```

若该正则匹配数量为 0 或明显异常(比如只有 2 个),尝试其他模式:`^第[0-9一二三四五六七八九十百]+[章节幕]`、`^Chapter`、`^[0-9]+\.`,用实际文件的章节标题格式为准。确定格式后,写一个切分脚本 `scripts/split_chapters.py`:
- 按章节标题行切分,每章存为 `analysis/chapters/ch_<编号>_<标题前8字>.txt`
- 输出章节总数和每章字数清单到 `analysis/chapter_list.md`

验收:章节文件数量与 grep 计数一致;抽查第 1、10、最后一章,开头是对应章节标题。

## Step 6:场景对照抽样(可行性核心验证)

从 `analysis/chapter_list.md` 中选章:
1. 通读每章**标题**(只读标题,不读全文),结合每章前 30 行的快速浏览,挑出:
   - 3 个明显的**战斗/动作章**
   - 3 个明显的**日常/校园/对话章**
   - 若无法从标题判断,用关键词密度辅助:战斗章 grep 计数「血|枪|爆|吼|撞|杀」,日常章计数「教室|食堂|宿舍|电话|咖啡」
2. 对这 6 章分别跑 `style_stats.py`,结果存 `analysis/scene_compare/<章文件名>.json`
3. 汇总成对照表 `analysis/scene_compare.md`,列出两类章节在以下参数上的均值对比:
   - 平均句长 / 短句占比 / 长句占比
   - 平均段落长
   - 对话字数占比
   - 感叹号、省略号频率

**可行性判定标准**(写入报告):
- ✅ 强可行:两类章节在 ≥3 个参数上差异超过 30%
- ⚠️ 弱可行:仅 1-2 个参数差异超过 30%(场景分类层降级为粗分类)
- ❌ 不可行:所有参数差异 <15%(统计层对场景区分无效,后续体系需改走纯 few-shot 路线)

## Step 7:n-gram 自检压力测试

1. 自己**原创**写一段 200 字的现代都市风格文字(不看语料、不模仿),存 `/tmp/original_sample.txt`
2. 从语料**任意位置**复制一句 20-30 字的原文,插入到上面文字中间,存 `/tmp/mixed_sample.txt`(此文件用后即删,不留在 analysis/)
3. 运行:

```bash
python3 scripts/ngram_check.py corpus/龙族1.txt /tmp/original_sample.txt 10
python3 scripts/ngram_check.py corpus/龙族1.txt /tmp/mixed_sample.txt 10
rm /tmp/mixed_sample.txt
```

验收:
- 纯原创样本:命中片段数 = 0
- 混入样本:命中片段数 ≥ 1,且命中内容正是插入的那句
- 记录两次运行在该语料体量下的**耗时**(用 `time` 前缀),写入报告——这决定以后每章自检的成本

## Step 8:可行性报告

汇总生成 `analysis/FEASIBILITY_REPORT.md`,必须包含:
1. 语料盘点结论(覆盖范围、是否需要补充语料)
2. 全书基准参数表(baseline 关键数字)
3. 场景对照结果 + 按 Step 6 标准给出的可行性判定(✅/⚠️/❌ 三选一,附依据)
4. n-gram 自检的准确性与耗时结论
5. 发现的所有异常和你做过的兼容性修改
6. 对下一阶段(完整四层体系)的建议:哪些层值得做、哪些建议降级或砍掉

报告中所有内容只允许统计数字、参数名和结构描述,**不得出现语料原文引用**。

## 异常处理预案

| 异常 | 处理 |
|---|---|
| 语料文件缺失 | 停止,汇报当前目录实际内容 |
| 编码转换失败 | 尝试 GB18030/GBK/BIG5 三种,均失败则停止汇报 |
| 章节正则全部失配 | 改用固定字数窗口切分(每 8000 字一段),在报告中注明"章节切分降级" |
| 脚本报错 | 修复重试最多 3 次,保留原始报错信息到 progress.md |
| 战斗/日常章无法区分 | 在报告中如实写"场景抽样失败",不要硬凑结论 |

## 最终交付

完成后汇报以下内容给我:
1. `FEASIBILITY_REPORT.md` 全文
2. progress.md 的完整记录
3. 一句话结论:✅ / ⚠️ / ❌ + 你的下一步建议
