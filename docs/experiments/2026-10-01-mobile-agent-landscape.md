# 移动端 agent 现状调研（为 B 路线选型）

**日期**：2026-10-01 · **用途**：决定"真实移动端 agent"这条路线做在哪个栈上
**结论先写**：**只有在"开源 + 可自建 + 载体可插桩"的那一类上，你那条通道才测得出来**；
商业厂商助手属于**不可插桩的闭环**，只能走授权后的黑盒测试（红线）。
本文所有外部信息都标了来源链接；**我未在本次检索中核到一手来源的，一律注明"未核对"**。

---

## 1. 三类栈，按"能不能插桩"排序

### 1.1 商业厂商助手（云端闭环，**不可插桩**）

| 厂商 | 形态 | 来源 |
|---|---|---|
| Apple | 下一代 Apple 智能 / **Siri AI**（2026-06 发布） | [Apple Newsroom](https://www.apple.com.cn/newsroom/2026/06/apple-unveils-next-generation-of-apple-intelligence-siri-ai-and-more/) |
| Google | Android 上的 **Gemini Intelligence**（主动智能）；官方博文谈"让 AI agent 更好地驱动 Android 应用" | [Google 博客（繁中）](https://blog.google/intl/zh-tw/products/android-chrome-play/android-gemini-intelligence/)、[Android Developers Blog 2026-02](https://android-developers.googleblog.com/2026/02/the-intelligent-os-making-ai-agents.html) |
| 华为 | 鸿蒙意图框架 **HMAF 2.0**：据该来源，小艺可调用 2100+ 系统能力、2000+ 鸿蒙智能体、500+ 伙伴 Skills，支持 MCP/A2A（HDC 2026） | [财富号报道](https://caifuhao.eastmoney.com/news/20260919103522660026450) |
| 小米 / OPPO / vivo / 荣耀 / 字节 | 小爱、小布、蓝心、YOYO、豆包手机等 | 月活/口碑排序见 [mydrivers 转载](http://m.mydrivers.com/newsview/1136281.html) |

**为什么不能用**：它们是**部署中的产品**、记忆与状态在**服务端**、策略由厂商控制——
你既拿不到载体，也拿不到清理规则。用它做测试 = 第 4 类（需厂商授权 + 协同披露）。

**但它们是你论文的"现实动机"**：

- 据报道，一次对 **7 个手机智能体**的测评显示：让 agent"点一杯奶茶"就需要交付**约 40% 的高敏权限**——
  [21 世纪经济报道](https://www.21jingji.com/article/20260224/herald/cc6eaebbb6f84c6b5e8317fd5ddbe2d8.html)；
- 一篇调查报道称"**浏览一封邮件，银行验证码就被盗**"，手机 AI 助手的安全漏洞引发争议——
  [经参调查（转载）](https://h.xinhuaxmt.com/vh512/share/12983103)；
- 行业分析谈"AI 手机的授权分野与制度围栏"——[36Kr](https://eu.36kr.com/zh/p/3987470711258119)；
- Siri 月均使用 **3.8 次**（QuestMobile 6 月手机 AI 助手数据，转引自 [antutu](https://www.antutu.com/doc/137198)）。

**对你的意义**：这些正好说明"手机 agent + 通知/短信/无障碍权限"就是现实攻击面，
**而你的装置测的是这条面上的持久化与规避机制**——动机一段可以直接引。

### 1.2 开源移动 agent 框架（**B 路线的候选**）

| 项目 | 形态 | 驱动方式 | 来源 |
|---|---|---|---|
| **DroidRun / mobilerun** | 开源、**LLM 无关**的移动 agent；自然语言控制设备；有 `DroidAgent` SDK | 见仓库文档（ADB/无障碍；**未逐一核对**） | [GitHub](https://github.com/droidrun/mobilerun)、[SDK 文档](https://github.com/droidrun/mobilerun/blob/main/docs/sdk/droid-agent.mdx) |
| **Android-MCP** | 轻量开源，把 AI agent 与 Android 设备桥起来（**MCP 形态**，便于接任意 LLM） | MCP + ADB | [PyPI](https://pypi.org/project/iflow-mcp_cursortouch-android-mcp/0.1.0/)、[Socket 分析页](https://socket.dev/pypi/package/android-mcp/overview/0.2.0) |
| **Mobile-Agent-v3** | 阿里 X-PLUG 系，"Fundamental Agents for GUI Automation" | GUI（多模态） | [论文](https://ar5iv.labs.arxiv.org/html/2508.15144)、[仓库](https://github.com/ThunderboltLei/X-PLUG-MobileAgent) |
| **UI-TARS-desktop** | 字节开源的多模态 agent 栈 | GUI（多模态） | [GitHub](https://github.com/bytedance/UI-TARS-desktop) |
| **AppAgent** | 腾讯，"Multimodal Agents as Smartphone Users"，操作手机 App 的多模态 agent 框架 | GUI（多模态） | [GitHub](https://github.com/TencentQQGYLab/AppAgent) |
| AutoDroid / M3A / T3A | 学术评测里常被并称的移动 agent（M3A、T3A 见下条基准） | 多为 GUI | M3A/T3A 出现在 [该评测](https://huggingface.co/buckets/huggingchat/papers-content/tree/2507/2507.04227.md)；AutoDroid **本次未核对** |

**对你的关键分野**：**DroidRun / Android-MCP 是"设备控制层"（脚本化 / MCP / ADB）**，
而 **Mobile-Agent-v3 / UI-TARS / AppAgent 是"像素 GUI 层"**。
你那条通道测的是**跨会话的指令持久化**，不是"会不会点按钮"——
**像素层会把可复现性打掉**（你现在最硬的资产是 571 个 run 全部可从 artifact 重算），
所以选型上优先**脚本化/无障碍/MCP** 那一类。

### 1.3 官方与端侧工具链（另一条干净路径）

| 项目 | 内容 | 来源 |
|---|---|---|
| **ADK for Kotlin / ADK for Android 0.1.0** | Google 官方：**在 Android 上构建 AI agent** 的工具链 | [Google Developers Blog](https://developers.googleblog.com/en/adk-kotlin-android-building-ai-agents/) |
| **Gemma 4（edge）** | Google 官方：把 agentic 能力带到边缘设备 | [Google Developers Blog](https://developers.googleblog.com/bring-state-of-the-art-agentic-skills-to-the-edge-with-gemma-4/) |

**价值**：想要"厂商认可的工具链 + 端侧模型（数据不出设备）"时走这条；
缺点是 agent 的记忆/持久化由框架决定，**能不能插桩要看它把状态放哪**。

---

## 2. 评测环境与"记忆"研究（与你的通道直接相关）

| 项目 | 是什么 | 为什么对你重要 | 来源 |
|---|---|---|---|
| **AndroidWorld** | 动态基准环境，"An Open World for Autonomous Agents"（ICLR 2025） | 成熟、被广泛引用；**做移动 agent 实验的默认底座** | [ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/01a83bc2f2732a58e6aa731e659e7101-Abstract-Conference.html)、[Google Research](https://research.google/pubs/androidworld-an-open-world-for-autonomous-agents/) |
| **MemGUI-Bench** | **移动 GUI agent 的"记忆"基准**，动态环境 | **最贴近你的问题**：它把"记忆"当成一等公民来测——说明"移动 agent 的记忆"已是公认研究对象 | [arXiv 2602.06075](https://browse-export.arxiv.org/pdf/2602.06075) |
| **STAMP** | 为移动 GUI agent **训练显式记忆**，可控可扩展的虚拟环境 | 提供"显式记忆"的构造与虚拟环境思路，**可借来做载体插桩的参照** | [arXiv 2605.29324](https://export.arxiv.org/pdf/2605.29324) |
| M3A / T3A | 动态交互环境中的移动 agent 评测对象 | 可作为对照基线 | [该评测列表](https://huggingface.co/buckets/huggingchat/papers-content/tree/2507/2507.04227.md) |

**同一条线上的安全研究**（此前已核）：持久化/自增强注入（[Zombie Agents](https://ar5iv.labs.arxiv.org/html/2602.15654#1)）、
记忆投毒（[Persistent Memory Poisoning on Harness-Based Agents](https://export.arxiv.org/pdf/2609.13889#3#1)）、
以及本工作所用宿主所来自的 [AgentDojo](https://ar5iv.labs.arxiv.org/html/2406.13352v3#1)。

---

## 3. 适配度总表（给 B 路线选型用）

| 项目 | 开源 | 驱动方式 | **载体/记忆可插桩** | 可跑本地模型 | 对你的适配度 |
|---|---|---|---|---|---|
| DroidRun / mobilerun | ✔ | 设备控制（ADB/无障碍，**待核**） | **待验证**（关键） | ✔（LLM 无关） | **首选候选** |
| Android-MCP | ✔ | MCP + ADB | **待验证** | ✔（接任意 LLM） | **首选候选（更轻）** |
| ADK for Android | ✔（官方） | Android 原生 | 取决于框架状态管理 | ✔ | 备选（官方路径） |
| Mobile-Agent-v3 / UI-TARS / AppAgent | ✔ | **像素 GUI** | 弱（观测是截图） | 部分 | **不推荐做主实验**（牺牲可复现性），可做"现实性对照" |
| AndroidWorld | ✔ | 环境/任务 | 环境状态可读 | ✔ | **做底座** |
| MemGUI-Bench / STAMP | ✔（论文/基准） | 记忆与虚拟环境 | **记忆是显式对象** | — | **做插桩参照与对照** |
| 商业厂商助手（Siri/Gemini/小艺/小布/小爱/蓝心/YOYO/豆包） | ✘ | 闭环 | **不可** | ✘ | **红线：需授权** |

---

## 4. 由此得到的选型建议

1. **底座用 AndroidWorld**（成熟、被引用、状态可读），**不要**从零自造模拟器。
2. **agent 层优先 DroidRun/mobilerun 或 Android-MCP**：开源、LLM 无关、以设备控制/ MCP 驱动，
   **能在不牺牲可复现性的前提下**把"会话 → 动作 → 参数 → 成败"落成 artifact；
   若它们的记忆是**显式对象**（对照 MemGUI-Bench / STAMP 的形态），你的**载体普查就能直接搬过来**。
3. **像素层（UI-TARS / AppAgent / Mobile-Agent-v3）只做"现实性对照"**，且要预先接受：
   n 会很小、重跑不可复现，读数只作方向性参考。
4. **第一个 spike 不是跑攻击，而是回答一个问题**：**我能不能把"助手自己的 durable 产物"读出来？**
   —— 能，B 路线成立；不能，这条路只能做授权后的黑盒测试。
5. **端侧模型**（Gemma 4 / 本地小模型）用于"模型规模轴"，数据不出设备，是最干净的隐私形态。
6. **商业产品**：只在拿到授权后、以协同披露为前提；**不先测后报**。

**下一步（待你点头）**：我写 `2026-10-01-b-route-feasibility.md`——把"载体可插桩性"的**判定标准**
写成可执行清单（要看哪些字段、落到 artifact 的哪些位置、怎样算通过），
再挑 DroidRun 与 Android-MCP 各做一次**只读**的最小 spike（装、连、读状态，**不注入任何载荷**）。
