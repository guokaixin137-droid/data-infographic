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

先根据已确认的选题完成统计，再填入核对过的数字。模板按照输入绘图。

| 字段 | 用途 |
| --- | --- |
| title、intro、kicker | 标题、导语和可选的范围或系列名。 |
| lang、footer_title | 设置文档语言和末尾来源区标题；中文和英文有默认标题。 |
| data_note | 首屏资料说明。整图模拟时注明“演示数据”；混合来源在对应图的 note 中分别标记。 |
| palette | 联网研究后填入五个颜色角色和网页参考，可直接影响 HTML、PNG、PDF。省略时使用内置色板。字段和可复制示例见[联网取色](palette.md)。 |
| metrics | 可选首屏指标数组。每项含 label、value，可附 refs。 |
| sections | 有序章节。每项包含 title、可选 summary 和非空 blocks；顺序即讲述顺序。 |
| method | 汇总口径、时间范围、覆盖和缺失说明。 |
| sources | 来源数组。每项使用唯一 id 和易读 label，按需加 locator（页码、表格范围、时间码）、excerpt 或原始 http(s) 链接 url。 |

每个图块指定 type、title，可加 unit、note、refs 或 wide（跨两栏）。refs 是来源 id 的数组。图块、指标、数据行和案例都可引用，重复引用会指向同一处。

| type | 输入 | 绘制方式 |
| --- | --- | --- |
| bars | rows，每行有 label、value | 横条以零为基线，支持正负数。适合排名与同口径分组。 |
| trend | rows，每行有 label、value | 按输入顺序等距绘制，并列出每个点的实际值。适用于等时间间隔；不规则间隔请先汇总或另绘时间轴。 |
| matrix | columns，以及带 label、values 的 rows | 每行数值数量与列数一致。正值使用主色，负值使用负值色，数字保留正负号。宽矩阵自动跨栏，超过 8 列拆成连续小表，共用同一色阶和行标题。 |
| cases | items，每项有 title、text，可附 refs | 为邻近图表补人物、事件或登记口径的实例。 |

图表输入用 JSON 数字，单位写在 unit；同一块使用同一单位。缺失标为 null，显示为长横线，折线也会断开。条形、矩阵和折线输入中的 0 会保留。数值需要预先按展示精度取舍。若需不同语言版，从同一套数字和来源生成不同内容稿，对照核对后分别导出。视觉定制可在项目副本中修改 [海报模板](../assets/poster.html)。
