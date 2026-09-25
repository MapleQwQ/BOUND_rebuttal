# E4new 过程记录

## 2026-09-24：原始数据可用性核查

- 核对投稿快照的 12 个 BOUND `cross_task_case_grouped.jsonl`：每个模型×折均为 100 个 case、500 条 generation，且 `code_generation_raw`、`code_block`、`import_modules` 字段齐全。
- 在根目录历史实验 `knowledgeEdit/results/rq2_cross_task_20260611` 找到三个模型的 Base 四折逐条 `rq2_details.jsonl`。每文件 500 条；同模型四份 Base 文件 SHA-256 相同，因此正式统计只读取或计数一次。
- 逐模型×折核对 Base 和 BOUND：500 个 generation ID 完全对应，`question` 逐 ID 相同。投稿快照 BOUND 原始代码生成文本与根目录另一份 `replication_package/BOUND` 的对应输出逐 ID 相同（12 文件各 500/500）。
- 阅读投稿快照 `bound/cross_task.py`：`extract_import_modules` 使用 `ast.parse` 辅助提取，失败时回退文本扫描；现有 RQ2 未保存语法质量指标，也没有 `compile` 质量检查。
- 记录 E0 已发现的投稿 RQ2 TeX 与当前归档结果差异。结论是完整仓库足以做新的 Base–BOUND 语法审计，投稿 replication package 单独不足；本轮没有计算语法有效率或修改历史结果。

## 2026-09-24：语法实验与提取 QA

- 新建 `script/run_syntax_audit.py`，固定 Python 3.10.20、完整 generation 分母、100 prompt × 5 trials × Base/BOUND 四折，以及 10,000 次 prompt 成组 paired bootstrap（seed 20260924）。只运行 `ast.parse` 与 `compile(..., "exec")`，不执行生成代码。
- 首轮按投稿时的 `code_block` 提取器检查后，抽样发现一些 ` ```python ` 围栏因生成未闭合而连同标记进入解析器，尤其影响 Qwen3。记录这一发现后，对 Base 和 BOUND 统一增加未闭合 Python fence 的恢复，并将普通无代码说明归入 `no_code`。旧提取器的结果保留作敏感性分析，未删除首轮不利结果。
- 最终脚本逐条保存 `per_generation.csv`，并写入输入文件 SHA-256、Python 版本、逐折与三模型等权汇总，以及配对 bootstrap CI。复核 7,500 条记录、15 个完整条件、每条件 500 个唯一 ID、四种互斥状态总和与 `parse_ok` 标记一致。
- 结果：三模型等权 Base 89.60%→BOUND 88.12%，差值 −1.48 个百分点（95% CI [−3.28, +0.35]）；Qwen3 86.40%→78.90%，差值 −7.50 个百分点（95% CI [−11.65, −3.25]）。逐折和其他指标见 `results/summary.md`。承认语法指标不能代表运行或任务正确性，也不能消除 E0 的 RQ2 版本差异。
- 额外 QA：逐条状态总数7,500，`no_code` 242、`compile_failure` 11；抽检 Qwen3 的 `no_code` 记录均为 `None` 回答，DeepSeekCoder 的 `no_code` 样本为拒答或纯说明文字。`compile_failure` 实例包括函数外 `await` 和重复关键字/形参。输入清单记录15份独立文件（每模型Base一次、BOUND四折），逐条CSV与汇总JSON的主指标一致。

## 2026-09-24：扩展至四种 baseline

- 应用户要求，在 `knowledgeEdit/results/rq2_cross_task_20260611` 找到 ROME、MEMIT、DINM、Full-FT 的三模型×四折原始 `rq2_details.jsonl`，共48份、24,000条。每文件500个唯一generation ID、100个prompt×5次，与对应Base的ID和题目文本逐条一致；投稿快照BOUND的代码文本与历史RQ2 BOUND逐条500/500一致。
- 新建 `script/run_baseline_syntax_audit.py` 复用既有提取与分类函数，不改动原 Base/BOUND 定义。生成 `baseline_per_generation.csv`、`baseline_input_manifest.json`、`baseline_syntax_summary.json`，按prompt做10,000次配对bootstrap并保存完整CI。
- QA：24,000行、48个条件各500行、每条件100个prompt×5次，状态/parse标志一致，逐折CSV计算与汇总JSON一致。抽样查看低值方法输出：ROME/DINM/Full-FT在部分模型与折中频繁出现`None`、乱码或重复文本；Llama-3.1 DINM少数AST通过输出仍可明显无意义。因此结果只解释语法质量和退化类型，不等于功能正确率。
- 三模型等权Syntax-Valid：ROME14.88%、MEMIT89.22%、DINM53.83%、Full-FT41.20%，与Base89.60%、BOUND88.12%一并列于`results/baseline_summary.md`。各模型、各折与No-Code等诊断必须同时呈现。

## 2026-09-24：BOUND 来源再次核对

- 用户明确要求 BOUND 的 RQ2 数据取自 replication package。复核 `results/input_manifest.json` 的12条 BOUND 输入路径，均在 `BOUND_rebuttal/replication package/BOUND/results/paper/cross_task_generalization/`；`script/run_syntax_audit.py` 的 `SNAP` 也指向该目录。新增 baseline 脚本只读取先前结果中的 BOUND 行，不从 `knowledgeEdit/results/rq2_cross_task_20260611/BOUND` 读取。
- 在 `script/run_baseline_syntax_audit.py` 增加显式来源断言：先前结果必须有6,000条来自投稿 replication package 的 BOUND 行，manifest 必须有12份同前缀文件。报告开头明确区分 BOUND、Base 和其他 baseline 的来源。此次仅增强来源校验和文字说明，未改变计算或数字。

## 2026-09-24：结果表格并入设计文档及逐格核对

- 按用户要求，把全部方法的主语法通过率、每折明细、完整分母诊断与配对区间写入 `design_and_results.md`，使该文件可独立查阅。
- 逐格比对机器汇总时发现 `results/summary.md` 的 BOUND 四折明细误抄了早期旧提取口径，尽管四折均值和总体结论使用的是最终统一提取口径。已将主报告与设计文档中的12个BOUND逐折值改为 `syntax_summary.json` 的最终数值；其余指标和逐条数据未改变。
- 自动核对设计文档的表1–3共6个方法行、15个逐折行、18个诊断行，以及表4差值/区间和主报告逐折表，均与对应JSON一致。

## 2026-09-24：Base原始输出重审与来源纠正

- 应用户要求，新增`script/run_base_syntax_reaudit.py`，重新读取三个模型的Base四折全部12份原始RQ2逐条文件，独立输出`base_reaudit_all_folds.csv`和`base_reaudit_summary.json`；主Base仍固定使用fold A的1500条原始回答，其他折只做来源敏感性。
- 发现先前“同模型Base四折文件SHA-256相同”的说法不再符合当前文件：DeepSeekCoder A折一条保存的`code_block`漏掉原始回答中的`pass`，B/C/D保留它；Qwen3 B折5条、C折4条`code_generation_raw`与A不同，保存的`code_block`却相同。四折仍有相同的generation ID与prompt文本。原因未确定，不能声称文件逐字节相同。
- 以fold A原始回答重提取的主Syntax-Valid再次得到DeepSeekCoder91.00%、Qwen3 86.40%、Llama-3.1 91.40%；1500条代码哈希与状态均与更新后的主审计逐条相同。若直接校验当前fold A保存的`code_block`，分别为90.00%、85.80%、91.00%。Qwen3 B/C折从各自原始回答重提取为85.60%，A/D为86.40%；DeepSeekCoder与Llama-3.1四折主口径一致。
- 修改`run_syntax_audit.py`：不再要求Base四折文件哈希相同，而是核对ID与prompt，记录四折输入哈希及逐条差异，固定A折主输入。重新运行主审计后Base/BOUND主结果和差值CI不变；修订`design_and_results.md`、`results/summary.md`中关于四折相同和旧`code_block`敏感性的表述，并新增`results/base_reaudit.md`。

## 2026-09-24：Base四折来源解释

- 阅读`scripts/materialize_rq2_base_folds.py`：它从每模型Base fold A复制结果文件到B/C/D，并在副本`case.json`写入`base_reused_from`和“Base model is fold-invariant; RQ2 uses the same held-out test100 per model.” 三模型的B/C/D `case.json`均实际包含该记录。
- 因此四折Base是为编辑方法四折结果表对齐而物化的副本，不是四次独立生成；当前的少量差异是归档内容漂移，产生时间/原因尚无法从现有记录确定。已将此区别写入设计文档和Base重审报告。

## 2026-09-24：用户指定的Base最差折敏感性口径

- 按用户要求，修改主审计脚本：从每模型四折Base归档的`code_generation_raw`统一重提取代码，按完整500条分母计算Syntax-Valid Rate，选择最低一折；并列时按A/B/C/D顺序选最早者。输入清单记录全部12份Base文件SHA-256、四折率、所选折及事后选择规则。
- 选择结果：DeepSeekCoder A（四折均91.00%）、Qwen3 B（A/B/C/D为86.40%/85.60%/85.60%/86.40%）、Llama-3.1 A（四折均91.40%）。每模型Base仍只计500条；BOUND仍来自投稿`BOUND_rebuttal/replication package/BOUND`的12份原始输出。
- 重新运行Base/BOUND主审计及四种baseline审计，重算全部Base相对差值和10,000次prompt成组bootstrap CI。所选Base三模型等权为89.33%，BOUND为88.12%，差值−1.22个百分点，95% CI [−3.05,+0.63]。Qwen3 Base为85.60%，BOUND−Base为−6.70个百分点，95% CI [−11.00,−2.40]。
- 更新`design_and_results.md`表1、表3、表4及三份结果报告；固定A折重审结果继续保留作来源对照。此口径是在看到四折语法结果后选择的敏感性分析，不作为预先指定的独立重复实验。

## 2026-09-24：再次独立重审Base，发现C折文件变动

- 应用户再次要求，从12份Base原始`rq2_details.jsonl`重新读取6,000条折归档记录，检查每折500个唯一generation ID、相同题目和prompt、每prompt五次、原始回答重提取后的`no_code`/AST/compile状态，并保留完整分母。修改`run_base_syntax_reaudit.py`，使独立审计与当前主审计均按最差折选取，同时保留固定A折对照。
- 发现Qwen3 C折文件在两次审计间改变：旧SHA-256为`fcb56d5d36cae512a0256384fd7737b74ea457ae2967ded74737e2ed581c74ca`，当前为`e5445819e719c21156b7257b0a0b9bbd8d5f0d647892bf07a200a41987e7ebcf`，mtime为2026-09-24 13:49:39 UTC。当前C折相对A折有12条原始回答不同而保存的`code_block`未变，其中11条AST通过→解析失败；抽查差异包括引号、冒号、等号等字符缺失。原因未知，不能把其低值解释为独立Base生成质量。
- 当前四折重审率：DeepSeekCoder均91.00%；Qwen3 A/B/C/D为86.40%/85.60%/84.20%/86.40%；Llama-3.1均91.40%。依用户指定规则现选A/C/A，Base三模型等权88.87%，Qwen3 421/500、No-Code 44、Parse-Failure 35。固定A折仍为89.60%，前次按A/B/A为89.33%。
- 重新运行Base/BOUND及四种baseline主审计并重算CI。BOUND仍从投稿replication package读取，三模型等权88.12%；当前BOUND−Base为−0.75个百分点，95% prompt paired bootstrap CI [−2.57,+1.12]。随后再次运行独立Base审计，所选1,500条与主审计逐条代码哈希、状态完全一致（差异均0）。更新结果表和报告，明确当前C折来源风险。
