# 使用离线竖版模板

模板把一个 JSON 内容稿渲染为自包含 HTML。所有样式、图表和来源索引均嵌在成品内。点图表旁的方括号可跳到来源条目，条目中的原始链接可以继续打开。无需联网即可阅读整图和本地出处说明。

## 制作和导出

以下命令在技能目录运行。实际使用时将内容稿和成品路径指向用户的项目目录。随附的 [维修日内容稿](../assets/example.json) 是可直接运行的虚构示例。

~~~sh
python3 scripts/render.py assets/example.json poster.html
node scripts/export.cjs poster.html poster.png poster.pdf
~~~

生成 HTML 只需 Python 3。第二行可选，按需要仅传 PNG 或 PDF 路径。导出需要 Node.js、Playwright（或 playwright-core）和 Chromium 系浏览器。优先使用宿主已提供的依赖；模块放在独立目录时可用 NODE_PATH 指向其 node_modules。需要指定浏览器时设置 INFOGRAPHIC_BROWSER 为可执行文件路径。无需安装服务、上传资料或启动本地网站。

模板的桌面宽度为 1200 像素，窄屏会改为单栏。PNG 默认宽 2400 像素，高度由内容决定。PDF 使用同一内容生成一张与海报等高的页面，图表和文字可放大。导出后检查恰好一页，并抽看首、中、尾三处。

## 填写内容稿

先定主图。把“读者能沿图指出什么关系”写成一个具体问题，再填入数据、短标签和来源。海报用一个 `lead` 跨栏呈现主图，余下图块按读者接下来要看的对比编组。旧内容稿也可继续渲染。

| 字段 | 用途 |
| --- | --- |
| title、intro、kicker | 标题、导语和可选的范围或系列名。 |
| lang | 填已确认的成品语言标签，如 `zh-CN`、`zh-Hant`、`en` 或 `ja`。双语同图填主语言，两种文案都写入要展示的字段。 |
| footer_title、palette.heading、sources[].records_label | 有相应区域时，用成品语言填写来源区标题、配色参考标题和展开索引的按钮文字。例如日文版可用「集計方法と出典」「配色の参考資料」「出典一覧を開く」。 |
| data_note | 首屏资料说明。整图模拟时注明“演示数据”；混合来源在对应图的 note 中分别标记。 |
| palette | 联网研究后填入五个颜色角色和网页参考，可直接影响 HTML、PNG、PDF。省略时使用内置色板。字段和可复制示例见[联网取色](palette.md)。 |
| metrics | 可选首屏指标数组。每项含 label、value，可附 refs。 |
| lead | 首屏的完整图块，与下表各类图块共用字段。只在这里放一次主图。 |
| sections | 有序章节。每项含非空 blocks，可加 title、summary、columns（1、2 或 3，默认 2）。图块标题已经说清问题时可以省略章标题。窄屏自动重排。 |
| method | 汇总口径、时间范围、覆盖和缺失说明。 |
| sources | 来源数组。每项使用唯一 id 和易读 label，按需加 locator（页码、表格范围、时间码）、excerpt 或原始 http(s) 链接 url。合集可加 records（每项含 label、url，可加 locator）、records_label（展开按钮文字）及 key（计算或检索口径），让网页版逐份回查。 |

每个图块指定 type、title。把标题下的短图说写入 `caption`，例如“带子越宽，表示该周修好的这类物品越多。” `unit` 写必要的单位或分母，`note` 留给局部例外。按实际需要填写，避免同一个发现重复出现。图说允许随屏幕换行。图内节点的 `label` 可写“给客户”这样的短词，`detail` 可补一项具体动作。图块可用 `wide` 跨栏，可用 `refs` 关联来源 id。指标、数据行和案例也可引用。

| type | 输入 | 绘制方式 |
| --- | --- | --- |
| bars | rows，每行有 label、value | 横条以零为基线，支持正负数。适合排名与同口径分组。 |
| columns | rows，每行有 label、value | 从零基线绘制等宽竖柱，适合件数、分组频数或“每份文档涉及几个主题”的分布。 |
| trend | rows，每行有 label、value | 按输入顺序等距绘制，并列出每个点的实际值。适用于等时间间隔；不规则间隔请先汇总或另绘时间轴。 |
| matrix | columns，以及带 label、values 的 rows | 每行数值数量与列数一致。正值使用主色，负值使用负值色，数字保留正负号。宽矩阵自动跨栏，超过 8 列拆成连续小表，共用同一色阶和行标题。 |
| flow | from、to 各列一组含 id、label 的节点，可加 detail、refs。links 的每项含 from、to（节点 id），可选 value。两侧可加 from_label、to_label。 | 每条连接都带非负数量时，带宽按同一比例绘制，节点默认显示相连数量之和。多标签共现可设 show_totals 为 false，在 detail 另写去重的记录数。全都省略 value 时，用等宽连线表达路径、职责或用途。单位、重复计数口径写在图边。 |
| units | total、非空 rows，行含 label、整数 value，可加 detail、refs、approx。可指定每行的点数 columns 和 show_as（fraction 或 percent）。 | 一格代表图例写明的一个单位。已知调查百分比时，用 100 格表示百分比，并在 detail 写实际样本人数。建议“约每十场抽一场”可画 1/10，并在该行设置 approx 为 true。有顺序的最后几项可用 fill_from 为 end，从末端点亮。 |
| intervals | domain 为刻度的两个端点，rows 的每行含 label、low、high，可附 refs。 | 在共轴上标出各区间的两个端点。在 unit 写清单位和含义，例如嘉宾报告的评分增幅。 |
| figures | rows，每项含 label、value，可加 suffix、detail、refs。 | 直接标记用时、单位不同的个案指标或只知道方向的结果。适合做主图旁的补充。 |
| cases | items，每项有 title、text，可附 refs | 原话、特殊口径或其他必须保留文字的个案旁注。 |

例如，访谈只给出工单处理后的两种去向时，可以这样表达。材料若另给了各自的工单数，再为每条连接填写 `value` 并标明单位。某条去向数量未知时保留未知，可在这张图使用等宽连线。

需要读出每条带的确切数量时，可在加权流图填写 `matrix_label`（例如“同时提及的集数”）。模板从同一组连接生成旁边的数值矩阵，手机上矩阵接在流图下面。显式的零显示为 0，未提供的组合显示为横线。

```json
{
  "type": "flow", "title": "哪些团队会接手工单？",
  "from": [{"id": "desk", "label": "服务台"}],
  "to": [{"id": "support", "label": "客户支持"}, {"id": "repair", "label": "维修组"}],
  "links": [{"from": "desk", "to": "support"}, {"from": "desk", "to": "repair"}]
}
```

图表输入用 JSON 数字，单位写在 unit；同一块使用同一单位。缺失标为 null，显示为长横线，折线也会断开。条形、矩阵和折线输入中的 0 会保留。数值需要预先按展示精度取舍。多语言分版用同一套数字和来源分别制稿、导出。检查实际图中的语言、字形和长标签换行，尤其留意图例及页尾。视觉定制可在项目副本中修改 [海报模板](../assets/poster.html)。
