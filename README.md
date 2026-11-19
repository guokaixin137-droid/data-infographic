# 数据长图 · data-infographic

用 Codex 把大量文章、报告、访谈、反馈记录、视频转录或表格做成竖版信息图。成品中的编号可以回查原文。Agent 还会在网上查看该主题或创作者的公开作品，把有依据的配色用到整张图。

## 安装

首次安装时，在 macOS 或 Linux 上用有仓库读取权限的账号登录 GitHub CLI（`gh auth login`），再把仓库克隆到个人 Skill 目录。

```sh
skill_root="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skill_root"
gh repo clone guokaixin137-droid/data-infographic "$skill_root/data-infographic"
```

## 在 Codex 里开始一张图

在新对话里附上材料，说明受众和用途。例如，你可以这样发起一个项目。

> 用 `$data-infographic` 把这一年的读者来信和书评做成一张竖版长图。先给我几个内容方向，用色参考这位书评博主的主页和专栏封面。我需要高清 PNG 和可以点开出处的 HTML。

每个新项目先确认一次选题方式。若你已经在请求里说明了偏好，Codex 会沿着该方式继续。

| 选题方式 | 你会看到什么 |
| --- | --- |
| **直接生成** | Codex 阅读资料，挑出值得讲的发现，配上能解释它们的对比和案例，直接交付成图。 |
| **先看方向，我来选** | Codex 通常列出 3–5 个有材料支撑的方向，说明各自能回答什么、可以怎样画。你可以只选一部分，也可以自拟方向。选定后，Codex 会围绕它们补齐相关数据、趋势和案例。 |

例如，在第二种方式里，你可以回复「我选读者反复提到的选书难点。请补上不同阅读人群的对比，再举两个原文案例。」之后想增加篇幅、调整配色或换导出格式，都可以沿用已选主线。

## 大量文本和联网配色如何处理

长文按来源、章节或记录分批阅读，再合并跨批出现的主题。一篇文章即使被切成十块，统计“多少篇提到”时仍只算一篇。结论可以指向页码、小节、行号、记录编号或时间点。本地文本可用随附工具生成带定位的 JSONL。[大批量文本工作流](references/large-text.md)

选题确定后，Agent 会打开相关公开网页。分析具名博主时，查其本人主页、代表作品或色彩规范；只有主题时，对照相应领域不同发布者的专题、报告和信息图。选定的颜色会用于背景、标题、条形、折线和矩阵，页尾附配色来源及必要的明暗调整说明。用户可以直接给品牌色或要求离线制作。[联网取色与色板示例](references/palette.md)

使用 Clipto 分享链接时，可通过当前会话已连接的 Clipto 工具读取转录，也可以直接附上导出的转录文件。默认采用资料中可核验的信息。做演示时可以明确允许模拟数值，成品会在相应位置标注。

## 看一张成品

这张图使用虚构的「社区维修日」记录。第一周修好 5 件，第三周修好 9 件，矩阵解释了新增的 4 件来自哪里。图中蓝紫色和浅金色分别取样自一份社区维修报告的第 12、13 页。点击预览可看原图。[示例数据和色板](assets/example.json) · [配色参考原页](https://openrepair.org/wp-content/uploads/2024/10/ORA-report-2024-The-rise-of-community-repair.pdf#page=12)

<a href="docs/repair-day.png"><img src="docs/repair-day.png" width="480" alt="社区维修日竖版信息图。三周共修好 21 件，相比第一周，第三周的灯具和衣物各多修好 2 件。"></a>

## 在本地复现示例

在仓库根目录运行以下命令，用 Python 3 生成 `poster.html`，双击即可离线阅读。

```sh
python3 scripts/render.py assets/example.json poster.html
```

导出 PNG 和 PDF 还需要 Node.js、Playwright（或 `playwright-core`）和 Chromium 系浏览器。首次配置导出环境时，可以在同一目录运行以下两行。

```sh
npm install --no-save --package-lock=false playwright
npx playwright install chromium
```

下面的命令会生成宽 2400 像素的 `poster.png` 和可放大阅读的单页矢量 `poster.pdf`。如果只需要一种格式，保留相应的输出文件名即可。

```sh
node scripts/export.cjs poster.html poster.png poster.pdf
```

要换成自己的数据，可以从示例 JSON 改起。图表类型、来源字段和浏览器路径设置见[模板与导出说明](references/rendering.md)。选题和核验流程见 [SKILL.md](SKILL.md)。
