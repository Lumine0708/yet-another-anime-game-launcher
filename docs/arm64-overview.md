# Yaagl ARM64 迁移总览

记录日期：2026-10-11。后续开发基于本 fork 的 `lumine-develop` 分支；本文件记录迁移范围、当前证据和推进顺序。

## 当前基线

| 项目 | 状态 |
| --- | --- |
| fork | [Lumine0708/yet-another-anime-game-launcher](https://github.com/Lumine0708/yet-another-anime-game-launcher) |
| 开发分支 | `lumine-develop`，跟踪 `origin/lumine-develop` |
| 同步来源 | [上游 PR #775](https://github.com/yaagl/yet-another-anime-game-launcher/pull/775)，截至记录日期仍为 open draft |
| PR 基点 | `784dda385c536286ef75f92e990514ac81509784`，与同步时 fork 的 `main` 一致 |
| 已导入提交 | `a8cc17783e422e87256c6c7080c340d532b70e93`，直接快进，保留原提交与作者 |
| 本轮交付 | 同步 PR、建立分支、添加总览；未修改游戏运行时 |
| 长期议题 | [上游 issue #725](https://github.com/yaagl/yet-another-anime-game-launcher/issues/725)，仍处于调查/规划阶段 |

## 目标与架构

目标是让 Apple Silicon 上的完整启动链路不依赖 Rosetta，同时保留 Yaagl 所需的游戏兼容补丁。

[Apple 的说明](https://support.apple.com/en-us/102527)是：Rosetta 通用支持持续到 macOS 27；macOS 28 起只为某些依赖 Intel 框架的老旧、无人维护游戏保留功能。不能据此假定 Yaagl/Wine 获得例外，也不能把它理解成禁止一切 x86 指令转译。

| 层次 | 当前路径 | 目标路径 |
| --- | --- | --- |
| 启动器和 macOS 辅助程序 | 默认 x64 构建 | ARM64 原生，沿用 #775 |
| Windows 系统接口 | 当前下载的 Intel Wine | 原生 ARM64 Wine，配套 ARM64EC/WoW64 支持及 Darwin 补丁 |
| 游戏 x86/x64 指令 | Rosetta 路径 | Wine 内集成的 FEX 转译器 |
| Direct3D 图形接口 | 当前 DXMT 或 D3DMetal | 先验证与所选原生运行时配套的 DXMT |
| 游戏兼容处理 | Wine 源码补丁、Windows PE 辅助程序、启动器补丁流程 | 按实际游戏逐项移植、验证 |

Wine 提供 Windows API，FEX 执行仍然是 x86/x64 的游戏代码；不要求游戏本身提供 ARM 版本。ARM64EC 用来连接原生 Windows 模块和被转译的 x64 代码，不能只把现有 Wine 的编译参数改为 `arm64`。

## #775 已经提供什么

具体构建命令沿用 [ARM64 构建说明](arm64-build.md)，不在这里维护第二份教程。

- `build-app.js`：通过 `YAAGL_BUILD_ARCH=arm64` 选择原生 Neutralino；通过 `YAAGL_SIDECAR_DIR` 覆盖本地重建的辅助程序，并检查打包进去的普通 Mach-O 文件包含 ARM64。
- `build-arm-sidecars.sh`：从固定来源构建 ARM64 aria2、xdelta；沿用现有 universal 7zz、hpatchz，不替换仓库内已提交的二进制。
- `build-sophon.sh`：选择 ARM64 Python，禁用 Nuitka 下载的 Intel ccache，遇到下载/编译错误停止。
- `YAAGL_BUILD_SUFFIX`：为本地实验生成独立应用名、bundle ID 和应用数据目录。
- `pnpm-workspace.yaml`：允许锁定依赖需要的安装脚本；两个锁文件未改变。

默认构建和发布仍为 x64。Windows PE 文件保持原样，后续由 Wine/FEX 执行。独立数据目录不等于可同时运行两个启动器：下载器仍使用端口 6868；现有自动更新也可能覆盖本地 ARM 构建。

## 运行时是否有可复用的开源实现

已有公开的原生 Wine/FEX/DXMT 构建路线，可以在此基础上做最小验证，无需从零写一套 macOS 模拟器；目前尚未选定或导入其中任何一套。

| 候选 | 可以复用的内容 | 证据边界 |
| --- | --- | --- |
| [Hadron](https://github.com/Broyojo/hadron) | 固定源码版本、Wine/FEX/DXMT 补丁队列、构建脚本和 loader 打包方式 | 作者报告在 macOS 27 运行部分 Steam 游戏；[游戏报告](https://github.com/Broyojo/hadron/blob/main/docs/test-games.md)不能证明 Yaagl 支持的游戏可用 |
| [MacNeutron](https://github.com/chadouming/MacNeutron/blob/main/wine-arm64/README.md) | Wine 11.19 的 ARM64/ARM64EC、FEX、原生 DXMT 构建与运行时检查入口 | [验收报告](https://github.com/chadouming/MacNeutron/blob/main/docs/testing/acceptance-arm64-ship-base.md)是作者环境结果，不是本 fork 的验证 |

复用范围先限定为运行时及其必要补丁，不引入候选项目的整套启动器、Steam 集成或与首个游戏无关的图形栈。

这些组件的开源代码可按各自许可证使用，无需购买 CrossOver。但源码许可与 Apple 的签名条件是两件事：[Hadron loader 签名说明](https://github.com/Broyojo/hadron/blob/main/docs/apple-developer-setup.md)及 MacNeutron 构建说明要求带跨架构 entitlement 的签名/profile；自行生成这种 loader 需要相应开发者资格。Hadron 另有仅支持 64 位程序的开发模式，不能直接当作完整兼容版本。

## 剩余阻塞点及其所在层

| 阻塞点 | 根源与已有解决方向 | 本 fork 接下来需要确认 |
| --- | --- | --- |
| Wine/FEX 不能作为两个独立程序直接拼接 | Wine 的 ARM64EC 调用边界、线程状态和 FEX UnixLib 需要配套；候选项目已有集成补丁 | 选定一组匹配的固定版本，先跑原生 Wine 和 x64 测试程序 |
| Windows 内存与 macOS 约束不同 | 低地址空间、4 KB 页、x18、JIT 写/执行切换及自修改代码涉及 Wine/FEX 的 Darwin 适配和 loader 权限 | 复用现有补丁并验证签名后的实际运行；不在 Yaagl 中另写 Windows 内存管理器 |
| x86 与 ARM 的内存顺序不同 | FEX 需保证 x86 TSO 语义；硬件 TSO 和软件屏障的选择影响性能与正确性 | 确认候选运行时实际启用的模式，先过内存顺序/线程测试，再测游戏 |
| 现有图形覆盖流程假定 Intel Wine | 启动器下载并覆盖 `x86_64-windows`、`x86_64-unix` 库，无法直接覆盖原生运行时 | 优先使用候选运行时配套 DXMT，避免旧 Intel 库覆盖它 |
| Yaagl 游戏兼容性尚未迁移验证 | Wine API 补丁、PE 辅助程序及游戏对异常、线程、自修改代码的依赖需要一起成立；Rosetta 本身不负责解决反作弊 | 对所选 Wine 基线逐项检查现有补丁，并在实际游戏中验证启动、登录和游玩 |

性能不能先下“必然更好/更差”的结论：原生 Wine 减少系统接口侧的转译，游戏仍需 FEX；TSO、调用边界、自修改代码和图形后端决定净结果。候选项目的微基准或其他游戏报告不能替代同一设备、同一游戏场景的比较。

已有源码适用性检查中，国服 `crypt32` 补丁、`WINE_ENABLE_TIMEOUT_FIX` 补丁在 Wine 11.17 和 Hadron 当时固定的 Wine 基线 `6880117619afdf62b4ccc40a8c6268c86613131f` 上通过了 `git apply --check`；一项 `mfreadwrite` 补丁未直接适用。补丁来源为 [riverfog7/macports-wine 的 crossover-wine 分支](https://github.com/riverfog7/macports-wine/tree/crossover-wine)。这只是补丁文本能否应用的检查，没有编译或游戏验证，也没有覆盖整个 Wine 发行版的补丁集。

移植前须以当前实际选用的 Yaagl Wine 发行版为依据，核对国服签名属性顺序、超时处理、媒体播放，以及该发行版使用的 `ntoskrnl`/WDF 兼容补丁。第三方报告中的“某游戏可启动”不能证明这些功能或反作弊链路已经验证。

## 后续具体改动入口

以下是运行时验证通过后可能需要的局部改动，本轮尚未实施；最终范围由所选运行时的实际接口决定。

| 文件 | 当前约束 | 最小接入方向 |
| --- | --- | --- |
| [`src/wine/distro.ts`](../src/wine/distro.ts) | 内置发行版指向现有运行时，没有原生 Wine/FEX 选项 | 增加一个经验证的实验运行时条目及确实需要的元数据 |
| [`src/wine/wine-install-program.ts`](../src/wine/wine-install-program.ts) | 解压到 `./wine`，初始化 prefix，失败提示安装 Rosetta | 保留原生 loader 所需 bundle/profile 结构，调整该运行时的初始化与错误提示 |
| [`src/wine/wine.ts`](../src/wine/wine.ts) | 选择 `bin/wine64` 或 `bin/wine`，按相邻路径找 wineserver | 先检查现有调用是否已足够；只有启动入口/环境不同才局部适配 |
| [`src/downloadable-resource.ts`](../src/downloadable-resource.ts) | DXMT 下载解压路径写死 Intel 库目录 | 对自带配套 DXMT 的原生运行时跳过旧下载流程 |
| [`src/clients/mhy/patch.ts`](../src/clients/mhy/patch.ts) | 安装/恢复 DXMT 时写入 Intel Wine 目录；复制 Steam PE 辅助程序 | 阻止旧 DXMT 覆盖原生库，逐项核对 PE 辅助程序支持情况，安装与恢复一起验证 |
| [`src/clients/mhy/hk4e/program-launch-game.ts`](../src/clients/mhy/hk4e/program-launch-game.ts) | 现有 Steam 启动选项、超时环境变量 | 优先保留既有流程，只改已证实不兼容的入口或参数 |

先在 #775 的独立应用数据目录中使用全新 prefix 做实验，保留现有安装。不要以重装运行时的方式试验旧 prefix：当前安装流程会删除目标 prefix。

## 推进顺序和验收

| 阶段 | 当前状态 | 验收与下一步 |
| --- | --- | --- |
| 1. 分支基线 | PR #775 已原样同步到 `lumine-develop` | 后续提交以此为基线 |
| 2. 原生启动器 | 构建入口已继承；本机尚未完整构建 | 按 `arm64-build.md` 构建，检查 Mach-O 架构、签名、UI、下载器和 Sophon |
| 3. 原生运行时最小验证 | 未开始 | 固定候选版本；确认 loader 签名条件；在独立 prefix 跑 wineboot、x64 程序、线程/内存和 D3D11 测试 |
| 4. 兼容补丁与首个游戏 | 未开始 | 编译包含所需补丁的运行时；记录游戏、区服和版本；依次验证启动、登录、进入场景与稳定游玩 |
| 5. 启动器接入 | 未开始 | 只接入已验证的运行时；验证安装、补丁、恢复、启动与更新不会混入 Intel macOS 组件 |
| 6. 性能与其他游戏 | 未开始 | 在相同硬件和场景对比旧路径；再验证 HSR、ZZZ，分别记录结果 |
| 7. 发布与 macOS 28 | 未开始 | 确定 ARM 产物命名和自动更新策略；在可用的 macOS 28 环境实际验收 |

下一轮先做阶段 2，再推进阶段 3；运行时最小验证通过前不铺开启动器改造。

## 验证记录与结论边界

本 fork 同步时执行了 `node --check build-app.js`、`bash -n build-arm-sidecars.sh build-sophon.sh` 和 PR 差异的 `git diff --check`，均通过。未进行依赖安装、TypeScript 检查、完整应用构建或游戏测试。

#775 的 [原始构建文档](arm64-build.md#validation-and-remaining-work)记录了作者的 24 个 Mach-O 组件架构、签名、aria2、xdelta 和 Sophon 检查结果。这些结果随 PR 保留，尚未在本机复现。

当前可以确认的是：ARM 启动器构建基线已经同步，公开原生运行时有可复用实现。尚不能确认的是：本 fork 已摆脱 Rosetta、Yaagl 游戏兼容补丁已经迁移完成，或 macOS 28 已可用。
