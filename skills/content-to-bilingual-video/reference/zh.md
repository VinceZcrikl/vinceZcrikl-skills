# Content to Bilingual Video（中文版）

用于把任意来源内容——文章、网页、HTML、PDF、X/Twitter 长文、用户粘贴文本等——整理成可复用 Markdown 知识资产，并进一步制作成带双语字幕的解说视频。

如果只是要摘要、翻译或归档，而不需要视频，不要使用这套完整流程。

## 核心理念

这不是“一次性把文章读成视频”，而是拆成三个彼此独立但关联的层：

1. **知识层**
   - 统一沉淀为 Markdown
   - 可写入 Obsidian、本地 Markdown 目录，或仅作为临时中间结果

2. **语音层**
   - 按 scene 拆分旁白
   - 每段独立生成、独立拟合、独立修音
   - 发音问题局部修，不要整条语音链路重做

3. **显示层**
   - 字幕文本独立于 TTS 文本
   - 双语字幕统一使用一个共享字幕框
   - 主语言在上，次语言在下，避免重叠

## 建议使用顺序

### 第一步：摄取内容源
先判断来源类型：
- 普通网页 / 文章
- HTML 页面
- PDF
- X/Twitter 内容
- 用户直接粘贴的文本
- 图文混合材料

然后提取：
- 标题
- 作者 / 来源站点
- URL 或本地路径
- 可用正文
- 必要图片或素材

如需更详细的来源与归档策略，参见：
- [source-ingestion-and-archival.md](source-ingestion-and-archival.md)

### 第二步：沉淀为 Markdown 知识资产
优先使用模板：
- [../templates/archive-note.md](../templates/archive-note.md)

建议至少包含：
- `## Source Information`
- `## Summary`
- `## Interpretation`
- `## Key Points`
- `## Cleaned Source`
- `## Video Thesis`
- `## Scene Candidates`

归档后端应可插拔：
- **Obsidian**：用户有 vault 工作流时
- **本地 Markdown 目录**：用户不使用 Obsidian，但希望落盘
- **不落盘**：用户只关心视频成品

注意：
- 即便不写入 Obsidian，也应把中间知识资产组织成 Markdown 结构
- 归档不是“原文转存”，而是“可复用知识整理”

### 第三步：抽象视频主线
在写 scene 之前，先回答：
- 这条视频真正要表达的核心论点是什么？
- 为什么这个论点值得讲？
- 证据、案例、对比点分别是什么？
- 观众看完后应记住什么？

把文章逻辑压缩成一个“视频主线”，再进入 scene 拆解。

### 第四步：拆成 scene-wise 旁白
优先使用模板：
- [../templates/scene-scripts.json](../templates/scene-scripts.json)

每个 scene 建议至少包含：
- `id`
- `title`
- `target_duration_sec`
- `spoken_text`
- `visual_goal`
- `pronunciation_overrides`
- `timing_strategy`
- `qa_notes`

这样做的好处：
- 某一句发音错了，只改那一段
- 某一段太长，只重写那一段
- 更容易做时长拟合
- 更容易与固定画面对齐
- 更容易迭代版本

如需更详细的按 scene 配音拟合策略，参见：
- [scene-wise-tts-fitting.md](scene-wise-tts-fitting.md)

## TTS 文本与字幕文本必须分离

这是本技能最重要的规则之一。

### TTS 文本
用于：
- 发音正确
- 节奏自然
- 时长可拟合

允许：
- 拼写拆分
- 音译
- pronunciation hacks

例如：
- `Markdown` → `Mark Down`

### 字幕文本
用于：
- 屏幕可读性
- 双语排版稳定
- 语言表达自然

默认不要自动继承 TTS 发音 hack。

只有在用户明确希望屏幕上也显示改写后的文本时，才同步改字幕。

## 发音修正的正确方式

当某个词读错时，不要粗暴全量重做。

正确顺序是：
1. 定位出问题的 scene
2. 只修改该 scene 的 `spoken_text` 或 `pronunciation_overrides`
3. 仅重生成受影响的 scene 音频
4. 重新合并 narration master
5. 先生成新的换音轨中间 MP4
6. 如有必要，再重烧字幕
7. 回到问题时间点复查

这样就能自然形成：
- `fixedvoice`
- `fixedvoice-v2`
- `fixedvoice-v3`

这种版本链路。

## 双语字幕的稳定形态

优先使用模板：
- [../templates/bilingual-subtitles-manifest.json](../templates/bilingual-subtitles-manifest.json)

推荐稳定形态：
- 一个统一字幕框
- 主语言在上
- 次语言在下
- 两种语言都在同一个卡片里
- 不重叠
- 保持安全边距

默认推荐：
- 中文在上
- 英文在下

如果 ffmpeg 直接字幕滤镜不稳定，优先考虑：
1. 生成透明 PNG 字幕卡
2. 每个 scene 或每个字幕节拍一张卡
3. 用 ffmpeg overlay 叠到视频上

如需版式细节与密度控制原则，参见：
- [bilingual-subtitle-layout.md](bilingual-subtitle-layout.md)

## 版本化原则

视频制作过程中，文件名必须表达“到底改了什么”。

典型阶段：
1. 基础视频
2. 换音轨中间版
3. 发音修正版
4. 双语字幕烧录版
5. 平台兼容最终版

推荐让文件名显式体现：
- TTS 引擎
- 是否已修语音
- 是第几次修音
- 是否为双语字幕版
- 是否为平台特供版

例如：
- `-cosyvoice2`
- `-fixedvoice`
- `-fixedvoice-v2`
- `-bilingual-stacked`
- `-telegram`

如需更系统的版本与验证策略，参见：
- [versioning-and-validation.md](versioning-and-validation.md)

## 最终验证清单

最终交付前至少检查两类问题。

### 一、技术验证
检查：
- 视频编码
- 分辨率
- 像素格式
- 帧率
- 音频编码
- 采样率
- 声道
- 时长
- MP4 atom 顺序
- faststart 是否生效

若目标是 Telegram 兼容，重点关注：
- H.264
- yuv420p
- AAC
- `moov` 前置

### 二、内容验证
至少抽查：
- 开头一个时间点
- 中间一个时间点
- 一个与已修问题直接相关的时间点

确认：
- 没有黑屏
- 没有画面错位
- 没有字幕重叠
- 双语字幕框样式正确
- 被修正的文字确实显示正确
- 被修正的发音确实听起来正确

## 常见误区

1. **把来源写死成 X/Twitter**
   - 正确做法：把输入抽象成任意可提取内容源

2. **把存储写死成 Obsidian**
   - 正确做法：Obsidian / 本地 Markdown / 不落盘 三种后端可切换

3. **把整条旁白当成唯一真相源**
   - 正确做法：scene-wise 维护，方便局部重做

4. **把 TTS hack 直接同步到字幕**
   - 正确做法：先分离 spoken text 和 display text

5. **修了语音，却还拿旧中间版去烧字幕**
   - 正确做法：字幕永远基于最新 voice-fixed intermediate

6. **字幕挡住画面时只会缩小字体**
   - 正确做法：先缩短文案、拆节拍、减小卡片高度，最后才缩字号

7. **渲染成功就当成片没问题**
   - 正确做法：必须做技术验证 + 抽帧 / 抽点内容验证

8. **系统故障不算视频流程问题**
   - 实际上如果 WebUI、SessionDB、文件句柄、maxfiles 等问题阻塞交付，它们就是生产链路问题，必须一起解决

## 一句话工作流

先把任意来源内容沉淀成统一 Markdown 知识资产，再抽象视频主线，按 scene 生成可修订旁白，独立维护双语字幕显示层，最后做版本化产出与技术/内容双重验证。
