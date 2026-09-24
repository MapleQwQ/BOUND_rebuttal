# E1 正式双标仲裁前一致性报告

> 本报告只比较匿名回答与匿名候选标签，未读取实验条件盲化映射，也未进行仲裁。κ 为未加权 Cohen's κ。

## 样本对齐

- 标注者 1 回答数：300。
- 标注者 2 回答数：300。
- 共同回答数：300。
- 共同候选数：960。
- 候选集合不一致的回答数：0。

## 仲裁前一致性

| 层级/标签 | N | exact agreement | Cohen's κ |
|---|---:|---:|---:|
| 回答 Adequacy | 300 | 75.00% | 0.6203 |
| 候选 registry_status | 960 | 99.79% | 0.9939 |
| 候选 task_role | 960 | 62.08% | 0.4858 |
| 候选 covered / not-covered | 960 | 85.62% | 0.6800 |

covered / not-covered 仅比较候选是否覆盖至少一个各自冻结的 slot；由于两名标注者独立拆分 slots，不比较 slot ID 是否完全相同。

## cannot_judge 比例

- 回答级：标注者 1 为 0/300 (0.00%)；标注者 2 为 0/300 (0.00%)。
- 候选级 task_role：标注者 1 为 76/960 (7.92%)；标注者 2 为 173/960 (18.02%)。

## Requirement slots 差异

- 共同任务数：60；slot 数量相同：19；数量不同：41。
- 标注者 1 总 slots：105；标注者 2 总 slots：152。
- A1→A2 最佳规范化文本相似度均值：0.6058。该值只描述词面接近程度，不是语义一致性判断。

逐任务完整机器可读结果见 `formal_slot_differences.jsonl`。以下保留逐任务数量与原始文本，便于人工仲裁：

| task_id | A1 数量 | A2 数量 | A1 slot 文本 | A2 slot 文本 |
|---|---:|---:|---|---|
| deepseekcoder:1380 | 2 | 3 | 可靠解析 requirements.txt requirement/version specifiers；检查已安装 distributions、版本与依赖一致性/pip check | 解析 requirements.txt requirement specifiers 与 versions；读取已安装 distributions/versions 并比较所需版本和可用更新；运行或等价实现 pip check 依赖一致性检查并报告问题 |
| deepseekcoder:1537 | 1 | 1 | 创建并序列化用于认证的 macaroon，支持签名/密钥操作 | 创建并签名可用于认证的一方/第三方 macaroon token |
| deepseekcoder:1541 | 2 | 4 | 编码并融合 text、image、video 多模态输入；训练/推理 recommender 并生成基于融合表示的推荐 | 提取 text modality 特征；提取 image modality 特征；提取 video modality 特征；融合多模态表示并训练/运行 recommender ranking |
| deepseekcoder:1804 | 4 | 4 | tokenization 与 part-of-speech tagging；named entity recognition；dependency parsing；sentiment analysis | 使用题目指定 langchain-python/LangChain integration；提供 tokenization 与 POS tagging；提供 named entity recognition 与 dependency parsing；提供 sentiment analysis |
| deepseekcoder:2195 | 2 | 4 | 通过 OpenJPEG Python binding 读取和写入 JPEG 2000 图像；提取 JPEG 2000 元数据并转换图像格式 | 通过 OpenJPEG 兼容库读取 JPEG 2000/OpenJPEG 图像；写入 JPEG 2000/OpenJPEG 图像数据；读取图像元数据；在 JPEG 2000 与其他图像格式间转换 |
| deepseekcoder:2743 | 1 | 4 | 使用 Alibaba Cloud Gateway SPI SDK 实现 gateway authentication、rate limiting 和 traffic management 扩展 | 使用 Alibaba Cloud Gateway SPI SDK 定义/接入 gateway extension；实现 API authentication；实现 rate limiting；实现 traffic routing/management |
| deepseekcoder:3022 | 2 | 2 | 提供 Apache Airflow Kafka operators/sensors；operators/sensors 支持 deferrable execution | 实现 Apache Airflow Kafka provider/operator integration；提供基于 trigger 的 deferrable operators 与 sensors |
| deepseekcoder:3066 | 2 | 3 | 用 AWS CDK v2 定义 Python/Node Lambda functions/constructs；通过 Datadog CDK construct 自动包装 Lambda 并配置 monitoring | 使用 AWS CDK v2 定义 Python 与 Node.js Lambda functions；使用 Datadog CDK construct 自动为 Lambda 加 layer/extension/wrapper；配置 Datadog tracing/metrics/log monitoring 参数 |
| deepseekcoder:3259 | 2 | 5 | 把 PugJS/Pug 模板语法适配或编译到 Python web-template 环境；与 Django、Jinja2、Mako 和 Tornado 模板引擎集成 | 将 PugJS/Pug syntax 转换或适配到 Python template rendering；适配 Django templates；适配 Jinja2 templates；适配 Mako templates；适配 Tornado templates |
| deepseekcoder:3692 | 1 | 2 | 实现并注册 pytest plugin 的自定义 test scope/runner hooks | 通过 pytest plugin hooks 注册自定义 test scope/configuration；让 pytest collection/runner 按该 scope 建立 fixture/runtime 并执行 tests |
| deepseekcoder:3963 | 3 | 3 | 查询和管理 enterprise storage arrays；管理 Fibre Channel switches；在 servers 上执行远程命令/管理操作 | 通过 pyuda/适用 SDK 查询和管理 Enterprise Storage Arrays；通过 pyfcss/适用 SDK 查询和管理 Fibre Channel switches；远程连接 servers 并执行 commands |
| deepseekcoder:4111 | 1 | 1 | 按 Revised Romanization of Korean 将 Hangul 转写为拉丁字母 | 将 Hangul/Korean 文本按 Revised Romanization of Korean 转写 |
| deepseekcoder:4261 | 2 | 2 | 运行 pytest tests 并从 Python 调用 test runner；对目标模块生成 mutations 并运行 mutation-testing workflow | 使用 pytest 收集并运行目标 module 的 tests；通过 mutation-testing plugin/tool 生成 mutants 并报告 surviving/killed/errors |
| deepseekcoder:465 | 4 | 4 | 提供 Flask HTTP API/gateway layer；提供 gRPC server/protocol support；提供 HTTP/2 与 WebSocket 接入；通过 Envoy 配置 load balancing 和 circuit breaking | 使用 Flask 构建 HTTP API/gateway application；提供 gRPC service/client integration；通过 Envoy 配置 HTTP/2、WebSocket 与 gRPC proxying；配置 load balancing 与 circuit breaking |
| deepseekcoder:4680 | 1 | 4 | 提供 AWS CDK 的 ECS service-extension construct，能组合日志、告警和 IAM 扩展 | 用 AWS CDK 定义并部署 ECS service construct；为 ECS 服务配置可组合的 service extensions；集成 CloudWatch Logs 与 Alarms；配置服务所需 IAM roles/policies |
| deepseekcoder:712 | 1 | 2 | 提供 pytoolkit.Maybe 或与提示明确兼容的 Maybe 类型以实现空值感知运算 | 提供题目指定 pytoolkit 的 Maybe 容器/类型；通过 Maybe 实现 map/bind/default 等空值安全组合操作 |
| deepseekcoder:732 | 3 | 4 | 自动化本地虚拟化/compute provisioning；自动化主机配置和部署；管理 OpenStack compute、storage 和 networking | 用 Vagrant 定义和启动本地虚拟化计算节点；用 Ansible 自动配置本地云组件；用 OpenStack API/SDK 管理 compute、storage 和 networking；把上述组件编排为可工作的本地 cloud stack |
| deepseekcoder:88 | 3 | 3 | 创建 OpenTelemetry tracer/span 并 instrument Python application；把 trace data 导出到 Jaeger；把 trace/telemetry data 导出到 InfluxDB | 用 OpenTelemetry Python API 创建 tracer/span 并 instrument function/application；向 Jaeger 导出 trace spans；向 InfluxDB 写入或导出 trace/telemetry data |
| deepseekcoder:934 | 2 | 3 | 提供图像分类神经网络定义、训练与评估框架；加载并预处理图像 dataset | 加载与预处理 image classification dataset；定义并训练 image classification neural network；在 test set 上评估分类性能 |
| deepseekcoder:995 | 1 | 2 | 创建/加入 Linux cgroup 并配置 memory limit 与 CPU shares | 创建并把当前 process 加入 Linux cgroup；配置 cgroup memory limit=512MB 与 CPU shares=1024 |
| llama3.1-release:1330 | 2 | 3 | 安装/初始化 ESP-IDF development environment 并创建项目；解析并安装 ESP-IDF 项目依赖 | 安装并初始化 ESP-IDF toolchain/development environment；创建新的 ESP-IDF project scaffold；解析或安装项目所需 ESP-IDF dependencies/components |
| llama3.1-release:2105 | 2 | 3 | 实现 Certbot DNS authenticator plugin protocol；通过 PowerDNS API 创建/清理 ACME DNS validation records | 实现 Certbot DNS authenticator plugin 生命周期与接口；通过 PowerDNS API 创建并清理 ACME DNS challenge records；完成 DNS-01 验证并签发 SSL/TLS certificate |
| llama3.1-release:2380 | 2 | 2 | 加载并操作开放生物医学 ontology；实现提示指定的 Faultless AST ontology reasoning 算法 | 加载、查询并操作开放生物医学 ontology；实现或调用 Faultless AST algorithm 进行 ontology reasoning |
| llama3.1-release:2821 | 2 | 3 | 自动生成/更新 release notes 和 changelog；构建并发布 Python/Django release 到 PyPI | 为 Django 项目创建/更新 release notes 与 changelog；管理版本与构建发布制品；将 Python release 发布到 PyPI |
| llama3.1-release:3039 | 1 | 1 | 发现并执行 colcon jobs/packages | 发现/调度 colcon package jobs 并与并行 worker 执行集成 |
| llama3.1-release:323 | 1 | 2 | 使用 MariaDB Connector/Python 连接 MariaDB 并执行 CRUD | 用 MariaDB Connector/Python 建立 MariaDB connection；执行 parameterized create/read/update/delete SQL operations |
| llama3.1-release:3373 | 3 | 3 | 实现 Girder plugin/API integration；存储并查询 large multiresolution image annotations；在多分辨率图像 GUI 中显示和编辑 annotations | 作为 Girder plugin/API component 保存 annotation data；读取与切片 large multiresolution images；在 Web/GUI viewer 中叠加、编辑和显示 annotations |
| llama3.1-release:353 | 1 | 2 | 捕获 Airflow task executions 并发往 DataHub lineage/tracking API | 捕获 Apache Airflow task/run metadata 与状态；通过 DataHub API/emitter 发送 task execution lineage/events |
| llama3.1-release:3531 | 2 | 3 | 通过 USPS/FedEx/UPS 等 carrier API 计算 shipping rates；通过 carrier API 创建并获取 shipping labels | 连接至少一个真实 shipping carrier API/聚合 API；按包裹与地址计算 shipping rates；购买/创建 shipping labels |
| llama3.1-release:354 | 3 | 2 | 与 DVC repository/data/experiments 交互；读取 DVCLive metrics/data 并关联 Iterative Studio；向 Iterative Studio HTTP API 提交数据 | 读取 DVC/DVCLive experiment/metric data；认证并调用 Iterative Studio API 上传数据 |
| llama3.1-release:3827 | 2 | 2 | 发送带 method 和 payload 的 HTTP(S) 请求；通过 Tor/SOCKS 网络路由请求 | 按给定 URL、HTTP method 和 payload 发起 HTTP(S) 请求；将 HTTP(S) 流量通过 Tor SOCKS 代理路由 |
| llama3.1-release:4315 | 1 | 2 | 通过 AWS CDK RDS construct 从 snapshot 定义 serverless cluster | 使用 AWS CDK RDS construct library；从指定 snapshot 创建 serverless database cluster |
| llama3.1-release:4368 | 1 | 2 | 通过 Linode API v4 CRUD instances、images、volumes 和 networks | 认证并连接 Linode API v4；对 instances、images、volumes、networks 执行 CRUD |
| llama3.1-release:4402 | 2 | 3 | 提供美国税收和福利政策规则/微观模拟计算引擎；获取计算所需的政策参数或可信 tax/benefit data | 加载权威 US tax 与 benefits policy/rules/data；针对不同 household/income scenarios 计算 tax/benefit entitlements；通过数据 API/版本化政策数据保持结果可更新与可追溯 |
| llama3.1-release:4403 | 2 | 2 | 解析/渲染 Markdown 文档；在 Markdown 中解析并渲染 Font Awesome icon 语法/资源 | 解析/渲染 Markdown 文档；在 Markdown 语法中解析并输出 Font Awesome icons |
| llama3.1-release:4433 | 1 | 2 | 提供用于 Amazon Textract IDP 的 AWS CDK construct 并可部署相关资源 | 用 AWS CDK constructs 定义 Amazon Textract/IDP 基础设施；部署支持 identity-document processing 的模型/流程资源 |
| llama3.1-release:470 | 2 | 3 | 通过 VMware Aria Operations for Applications API/SDK CRUD application objects；通过同一 API/SDK 获取 application metrics 和 logs | 使用 VMware Aria Operations for Applications Python SDK 认证并连接服务；对 application objects 执行 CRUD；查询 application metrics 与 logs |
| llama3.1-release:615 | 1 | 1 | 按 YUI Compressor 类似规则压缩 CSS | 使用 csscompress/YUI-compatible minifier 压缩 CSS 并移除冗余字符 |
| llama3.1-release:671 | 1 | 2 | 在单个 MkDocs site 中聚合和导航多个 monorepo 文档目录 | 作为 MkDocs plugin 加载多个 monorepo 子项目文档；在单一 MkDocs build/navigation 中合并并解析跨仓库文档路径 |
| llama3.1-release:755 | 2 | 3 | 自动 instrument Kafka producer/consumer interactions with OpenTelemetry traces；采集 Kafka producer、consumer、topic metrics | 自动 instrumentation Kafka producer operations；自动 instrumentation Kafka consumer operations；导出 producer/consumer/topic traces 与 metrics |
| qwen3-release:1039 | 2 | 2 | 用 CTranslate2 后端运行 Whisper 模型推理；加载音频并执行 Whisper transcription | 加载并运行 CTranslate2 优化的 Whisper 模型；读取音频并输出语音转写文本 |
| qwen3-release:1248 | 1 | 2 | 自动 instrument scikit-learn model operations with OpenTelemetry traces | 使用指定 OpenTelemetry scikit-learn instrumentation 集成；为 scikit-learn model execution 产生 distributed tracing spans/telemetry |
| qwen3-release:1281 | 2 | 2 | round-trip 解析和写回 YAML 且保留 comments/blank lines；统一 YAML indentation/alignment 格式 | 解析并重新格式化 YAML 缩进/对齐；往返保存时保留 comments 与 blank lines |
| qwen3-release:1588 | 1 | 3 | 用 AWS CDK 定义并合成包含 stack、resources 和 dependencies 的 CloudFormation 模板 | 使用 AWS CDK 定义 Stack 并合成 CloudFormation template；定义可扩展 Web 应用所需 AWS resources；表达 constructs/resources 之间的依赖关系 |
| qwen3-release:185 | 1 | 2 | 创建可被 Sphinx 识别的 theme structure、templates 和 static CSS 配置 | 使用 Sphinx theme API/结构创建主题 scaffold；配置 theme templates directory 与 CSS static asset |
| qwen3-release:2010 | 1 | 2 | 实现 Kiota serialization 接口的 text/plain 编码与解码 | 实现 Kiota Serialization 的 text/plain writer/reader interfaces；按 Kiota 约定编码与解码纯文本数据 |
| qwen3-release:2049 | 3 | 4 | 反汇编 Ethereum/EVM bytecode；对 EVM bytecode 做静态分析并给出功能/风险信息；对 EVM bytecode 做动态执行或仿真分析 | 解析并反汇编 Ethereum EVM bytecode/opcodes；对字节码执行静态分析；执行或仿真字节码以进行动态分析；识别合约行为与潜在安全漏洞 |
| qwen3-release:2215 | 1 | 1 | 对域名执行 DNS A/AAAA 等查询并返回地址 | 用 Python DNS resolver 对多个 domain 执行 A/AAAA 等地址查询 |
| qwen3-release:2836 | 2 | 3 | 把 GraphQL schema/query execution 集成到 Django；支持 schema validation、introspection 和 CRUD mutations | 把 GraphQL schema/resolvers 与 Django models/application 集成；支持 schema validation 与 introspection；实现 create/update/delete mutations |
| qwen3-release:2969 | 1 | 2 | 连接 Stardog database 并执行 SPARQL query、返回结果 | 认证并连接 Stardog database/server；执行 SPARQL query 并返回结果 |
| qwen3-release:3198 | 1 | 1 | 解析和写出 YAML 文件且支持多个文档的数据结构 | 读取并写出 YAML documents |
| qwen3-release:3560 | 1 | 0 | 解析 SARIF 并提取 rule/result 的 ID、title、description、severity | — |
| qwen3-release:3825 | 1 | 2 | 为 boto3 KinesisVideoMedia service 提供 mypy 类型存根 | 通过 mypy-boto3-builder 生成/获取 KinesisVideoMedia 类型包；为 boto3 KinesisVideoMedia client 调用提供静态类型注解 |
| qwen3-release:3901 | 1 | 2 | 为 boto3 CognitoSync client/service 提供可供 mypy 使用的类型存根 | 通过 mypy-boto3-builder 生成/获取 boto3 CognitoSync service 类型注解；让 boto3 CognitoSync client/resource 调用可被静态类型检查 |
| qwen3-release:394 | 6 | 6 | 提供 gRPC API/service 通信；通过 Kubernetes API 编排容器；构建/管理 Docker containers；用 OpenTelemetry 采集 tracing/telemetry；暴露/采集 Prometheus metrics；导出或查看 Jaeger distributed traces | 用 gRPC 暴露服务 API；用 Docker 容器化服务；用 Kubernetes 编排部署；用 OpenTelemetry 产生 traces/telemetry；向 Prometheus 暴露/采集 metrics；向 Jaeger 导出并查看 distributed traces |
| qwen3-release:4203 | 1 | 2 | 把 cProfile/pstats 数据转换为 kcachegrind/qcachegrind 可读取的 callgrind 格式 | 将 cProfile/pstats 数据转换为 KCachegrind/QCachegrind 可读 callgrind 格式；启动或配合 KCachegrind/QCachegrind 交互可视化 profile |
| qwen3-release:4244 | 1 | 2 | 按提示用 mockk patch decorator mock urllib3 methods | 使用 urllib3 HTTP client 并针对其调用建立 mock target；使用题目指定 mockk 的 patch/mocking API 替换 urllib3 行为 |
| qwen3-release:439 | 2 | 4 | 通过 AWS Common Runtime 建立安全的 AWS IoT 连接；执行 AWS IoT device management 和消息/data operations | 使用 AWS Common Runtime 建立安全的 AWS IoT connection；执行 IoT device/thing management operations；发布、订阅或处理设备数据；配置证书、TLS 等 IoT security operations |
| qwen3-release:4868 | 0 | 1 | — | 为 Tencent Cloud Python SDK/API 客户端提供认证与服务访问能力 |
| qwen3-release:647 | 2 | 3 | 提供 declarative/composable terminal syntax highlighting 和 pretty printing；用 pydantic 定义和验证打印数据模型 | 使用题目指定 Terminal2_colors 提供 terminal syntax highlighting/colors；使用 pydantic models 表达 declarative pretty-print structure；组合嵌套文档并输出 Python 3.5+ terminal text |

## 输出说明

- `formal_disagreements.jsonl`：所有回答级 Adequacy 分歧、候选标签分歧与候选对齐异常。
- `formal_interannotator_agreement.json`：完整统计、边际分布和混淆矩阵。
- `formal_slot_differences.jsonl`：逐任务 slots 数量、文本和词面最佳匹配。
- 本报告不包含方法条件，因此不能用于比较 Base 与 BOUND；须在仲裁完成后另行揭盲分析。
