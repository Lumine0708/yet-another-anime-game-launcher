# ARM64 本机验证记录

日期：2026-10-11。设备：Apple M5 MacBook Air，16 GB，macOS 27.2（26B5101f）。
基线：`lumine-develop`，`9888364`。本轮沿用 #775 的构建入口；默认发行版和生产 Wine/prefix 未替换。

验收范围为国服原神 7.1.0 的未登录启动及持续运行。没有执行登录、接受游戏协议、进入账号或游玩操作；不对登录后的兼容性作结论。

## ARM 启动器

产物位于仓库根目录 `Yaagl ARM.app`，bundle ID 为 `com.3shain.yaagl.arm`，数据位于 `~/Library/Application Support/Yaagl ARM`。

构建使用原生 Node 22.23.0、pnpm **10.15.1**、ARM64 Python 3.13.13，编译并发为 2。
pnpm 11 不再按本仓库的 `onlyBuiltDependencies` 安装脚本，因此本轮显式使用 `corepack pnpm@10.15.1`；未修改锁文件或 workspace 配置。

```sh
corepack pnpm@10.15.1 install --frozen-lockfile
bash configure.sh
YAAGL_BUILD_JOBS=2 bash build-arm-sidecars.sh
YAAGL_BUILD_ARCH=arm64 YAAGL_BUILD_JOBS=2 bash build-sophon.sh
# build-app.js 内部也调用 pnpm，须确保 PATH 中的 pnpm 是 10.x。
YAAGL_BUILD_ARCH=arm64 YAAGL_CHANNEL_CLIENT=hk4ecn \
  YAAGL_BUILD_SUFFIX=ARM YAAGL_SIDECAR_DIR="$PWD/.arm64-build/output" \
  YAAGL_VERSION=0.3.18-arm-local node build-app.js
codesign --force --deep --sign - 'Yaagl ARM.app'
codesign --verify --deep --strict 'Yaagl ARM.app'
```

已验证：

- `tsc` 通过；现有 Vitest 56 项测试通过（`vitest run --threads=false`）。
- 启动器及 sidecar 中 24 个普通 Mach-O 均包含 ARM64；deep/strict 签名验证通过。
- 实际打开 UI；首次安装界面及下载进度正常。忽略官方自动更新，以保留本地实验构建。
- 强制 ARM64 执行打包的 aria2，端口 16868 的 JSON-RPC 返回 1.37.0。
- 强制 ARM64 执行打包的 Sophon，端口 18000 的 `/health` 和国服 `/api/game/online_info?game=hk4e&reltype=cn` 成功，返回 7.1.0。

**该应用仍使用原有默认 Intel Wine 安装流程。** 首次启动会自动下载它；本轮在下载阶段关闭，未执行安装配置。原生运行时还没有接入该应用，不能据此宣称 ARM 游戏启动链路完成。

脚本已实际验证短时限退出及 SIGTERM 中断清理；并发启动同一实验运行时会退出 2，原观察继续。具体证据在 `.arm64-build/logs/probe-short-metrics.json`、`probe-interrupt-metrics.json`、`probe-concurrent-refusal.log`。最终短时验证记录 `cleanup_errors=[]`、`remaining_processes=[]`；独立 Tester 另模拟了 wineserver 超时和执行错误，确认仍继续清理客户端并保存指标，最终只读核对两套实验运行时均无残留进程。

本机组件证据保存在 `.arm64-build/logs/launcher-architectures.json`、`component-checks.log`、`aria2-native.log`、`sophon-native.log`。完整构建日志在 `/tmp/yaagl-arm-*.log`。

## 复用来源和固定版本

先查 [YAAGL #725](https://github.com/yaagl/yet-another-anime-game-launcher/issues/725)、[YAAGL Wine](https://github.com/yaagl/anime-game-wine)及其指定的 [macports-wine](https://github.com/riverfog7/macports-wine/tree/crossover-wine)。YAAGL 当前提供的运行时仍为 Intel。

[YAAGL #734 的社区记录](https://github.com/yaagl/yet-another-anime-game-launcher/issues/734)推荐 `11.0-1 Crossover + Steam Patch + timeout fix`。原安装也是这个组合。本轮复用仓库中已有的签名 `steam64.exe`、`lsteamclient64.dll` 和 DWCA 根证书，不下载替代版 `mhypbase.dll`。

| 候选 | 发布产物 SHA-256 | 源码基线 |
| --- | --- | --- |
| [Hadron v0.2.0](https://github.com/Broyojo/hadron/releases/tag/v0.2.0) | `02de69e7886e39748595a8ed7e8683d8392e1f7340fa7515bcb72c19f3db5ce6` | Hadron `74d94f3f2756da0bd496d9dfeb0bd195f6265e8c`；Wine `6880117619afdf62b4ccc40a8c6268c86613131f`（11.18）；FEX `0df84d3844bcdb87bb7d3f5b8fb0959cd009c038`；DXMT `e86484e585a00d33f2750f96ff7c1ff56bccb06d` |
| [MacNeutron v0.4.0](https://github.com/chadouming/MacNeutron/releases/tag/v0.4.0) | `8ae509f2020da65e57771ad5f3557e4d69b0af8a1c3f65a72f16b4218e36064f` | Wine 11.19 `455e3509b98a6919fd4ad1def4803e08c41c03b2`；FEX `4ed80fd07176dce976a7351f559d59a47b68cbae`；DXMT `1fba8d25b5e29ab49012d633676a6b0d4b3b96c5+45fa192ccc0a` |

两个下载均核对 SHA-256。只解出运行时，保留已签名 loader、profile、符号链接及许可证；未安装其 Steam 集成，也没有启动其产品 UI。两个 loader 的签名和跨架构 entitlement 均已检查。Wine/FEX/DXMT 使用发布包配套组合，未导入旧 Intel Mach-O 图形库。

签名 loader 可以复用，因此这些本机运行实验不需要申请开发者权限。自行重建、签名 loader 的条件仍按各项目说明。

## 隔离准备

本机路径：

| 内容 | 相对仓库根目录路径 |
| --- | --- |
| Hadron 运行时 | `.arm64-build/runtime/hadron-v0.2.0`（含 `dist/`） |
| MacNeutron 运行时 | `.arm64-build/runtime/macneutron-v0.4.0/MacNeutron.app/Contents/Helpers/wine.app` |
| Hadron prefix | `.arm64-build/prefix-hadron` |
| MacNeutron prefix | `.arm64-build/prefix-macneutron` |
| 原神副本 | `.arm64-build/game-cn` |
| 测试程序及本机命令 | `.arm64-build/tests`、`.arm64-build/tools` |

游戏从 `/Volumes/Lumine_2T/mihoyo/GameBodies/Genshin Impact Game` 用 `cp -cR` 克隆到同一 APFS 卷，逻辑大小约 142 GB；修改副本时使用写时复制。两个 prefix 均由对应原生 Wine 新建，没有复制生产 prefix、注册表或账号数据。

准备沿用 YAAGL：在副本中将 `YuanShen_Data/upload_crash.exe`、`YuanShen_Data/Plugins/crashreport.exe`、`YuanShen_Data/Plugins/vulkan-1.dll` 改名为 `.bak`；将现有 Steam PE 辅助程序复制到实验 prefix 的 system32，按现有流程复制 `HoYoKProtect.sys`。没有改动原游戏文件、`/etc/hosts` 或生产 Wine。

Hadron 在自身外部 `dist/share/wine/wine.inf` 中加入 YAAGL 的 DWCA 根证书后运行 `wineboot -u`。MacNeutron 的签名 bundle 保持原样，证书只导入新 prefix；按它的 [检查入口](https://github.com/chadouming/MacNeutron/blob/v0.4.0/wine-arm64/check.sh)设置 `HKLM\Software\Microsoft\Wow64\amd64` 默认值为 `libarm64ecfex.dll`，将同一 bundle 的 `DXMT/aarch64-windows` DLL 放入 system32，使用其图形 overrides 和 `WINEMSYNC=1`。

这些本机准备命令保存在 `.arm64-build/tools`；它们是实验材料，包含本机绝对路径，不是发行版安装器。换设备需要重新准备。

## 原生运行时最小验证

x64 测试由 ARM64 宿主的 mingw-w64 14.0.0 编译，复用 [Hadron tests/win](https://github.com/Broyojo/hadron/tree/v0.2.0/tests/win) 的 hello、thread-allocation、d3d11tri，以及 [MacNeutron tests](https://github.com/chadouming/MacNeutron/tree/v0.4.0/wine-arm64/tests) 的 x64-litmus、x64-smc。

| 测试 | Hadron | MacNeutron |
| --- | --- | --- |
| 全新 prefix 的 wineboot | 退出 0 | 退出 0 |
| x64 hello | 报告 x86_64 guest、native machine `aa64` | 同左；须先注册 FEX |
| 线程/地址分配 | 退出 0 | 退出 0 |
| MP、LB、2+2W、IRIW | 各 10,000 次，forbidden 均为 0 | 同左 |
| RWX 与 `.text` 自修改代码 | 两项均从返回 1 变为 2，`PASS x64-smc` | 同左 |
| D3D11 / HLSL | 创建 FL 11.0 设备、编译 shader，5 秒绘制 161 帧 | 同样成功，185 帧 |

默认保留 FEX 的软件 TSO，未开启 Hadron 的可选硬件 TSO。10,000 次 litmus 是有限检查，不能证明任意并发或整个游戏正确。D3D11 帧数用于证明绘制发生，不是两套运行时的性能比较。

日志在 `.arm64-build/logs`：`wineboot.log`、`hello-x64.log`、`thread-x64.log`、`litmus-x64.log`、`smc-x64.log`、`d3d11-x64.log`，MacNeutron 对应文件加 `macneutron-` 前缀。

## 原神结果与继续方向

**Hadron 实验路径已到未登录主页初始化，持续 150 秒且窗口 API 有响应；真实画面和跨应用切换仍未完成验收。MacNeutron 仍有 Logo 崩溃。**

以下为发布包基线及初始诊断结果；当前本地候选配置见后续章节。

- Hadron：日志完成 Unity、D3D11、输入及资源初始化，经过 Logo，进入 `Home LoadScene`。两轮 120 秒实验没有自行退出，随后主动关闭。隔离 prefix 中的 Windows API 探针确认存在可见的 1920×1080 游戏客户区，但 `WM_NULL` 超时、窗口无响应。2 秒原生采样报告 `Code Type: ARM64`，映射了 `libarm64ecfex.so`；不能把进程驻留当成正常运行。
- Hadron + `FEX_SMCCHECKS=full` / `FEX_DISKCACHE=0`：没有解决，出现 `loader_section` 和另一临界区的等待超时；120 秒后关闭。
- Hadron + `FEX_O0=1` / `FEX_MULTIBLOCK=0` / `FEX_DISKCACHE=0`：仍未正常启动，120 秒后关闭；JIT 地址映射保存在 `.arm64-build/logs/genshin-hadron-o0-perf.map`，供后续定位。
- MacNeutron：完成 Unity/D3D11 初始化，随后在 `GameManager ShowLogo` 阶段出现 `Crash!!!`，Steam 辅助程序退出 5。该轮观察约 89 秒；不算稳定运行通过。

Windows 窗口探针、原生采样和游戏日志都在 `.arm64-build/logs`。MacNeutron 的游戏自身崩溃记录保留在新 prefix 的 `drive_c/users/lumine/AppData/LocalLow/miHoYo/原神/output_log.txt`。`driverError.log` 的旧条目来自游戏克隆，不能当作本轮新失败。

现有 Crossover 补丁包含 Rosetta 专用的代码失效处理，不能整体搬到 FEX。本机已在 Wine 11.18 加上 Hadron 的 26 项补丁，再应用 YAAGL 指定 macports-wine 的国服 `crypt32` 签名属性顺序补丁和 `gi-timeout/0009`。`make -j2 dlls/crypt32/all dlls/ws2_32/all` 通过，ARM64X DLL 与 ARM64 `ws2_32.so` 只部署到 Hadron 的隔离 dist/prefix。原签名 loader 和 MacNeutron bundle 未改动。网络 timeout 补丁不处理 `NtGetContextThread` 等待，媒体补丁仍未迁移。

本机使用官方 llvm-mingw 20260922 的 ARM64EC clang 23.1.2 和 bison 3.8.2 编译；工具链归档 SHA-256 为 `52e5f5a7b131021d0c39a37a38fa380a1da7885cd04bd61afd0cd4ecfb8bc1f3`。源码、构建目录、原始库备份与日志均保存在 `.arm64-build`；不是发行版运行时。

### 当前诊断证据

- [YAAGL #763](https://github.com/yaagl/yet-another-anime-game-launcher/issues/763) 的 7.1 元数据重复文件修复线索已核对：副本的 Managed/Native `global-metadata.dat` 哈希相同，不需要再次复制。
- Hadron 当前使用本地 GS selector 候选补丁：ARM64EC 的 64 位 GS 写入保留 Windows TEB，并允许读回 selector。局部差异保存为 [`arm64-experiments/fex-gs-selector.patch`](../arm64-experiments/fex-gs-selector.patch)，对应源码文件采用 MIT 许可，附 [FEX 许可](../arm64-experiments/FEX-LICENSE)，FEX DLL SHA-256 为 `baf6c1b9591162dfd14677f7c030fb5e8c3c2e3f944ede40052dcd8e04ee0b44`。`gs-selector-final.log` 验证 selector 0/0x2b、TEB 地址保持相同；最终 DLL 的 x64 SEH 与 C++ 异常测试均 PASS。非法 selector、跨原生调用恢复等行为未完整验证；它尚未单独解决 Home 挂起，不可当作已验收游戏补丁。
- Hadron 的服务端跟踪确认：调用线程请求暂停目标线程并读取上下文，目标进入 `THREAD_WAS_SUSPENDED` 后没有提交上下文，调用方保持 `PENDING`。最小 `thread-context-trace.exe` 中，阻塞等待线程的 20 次暂停/读取/恢复通过，纯计算循环第一次读取便挂起。关闭磁盘缓存及多块编译后仍挂起；增加 `FEX_MAXINST=1` 或 `2` 后两种线程均通过。日志为 `context-baseline-trace.log`、`context-single-block.log`、`context-one-instruction.log`、`context-two-instructions.log`。
- [FEX #4860](https://github.com/FEX-Emu/FEX/pull/4860) 明确说明条件跳转/间接跳转尚未作为暂停检查点，原因是上下文重建问题。当前源码的条件跳转路径也没有该检查。上述结果支持继续诊断该路径；不能据此直接在条件分支中插入中断并认定上下文正确。
- 在 `FEX_MULTIBLOCK=0`、`FEX_MAXINST=1` 下，Hadron 的实际原神首次记录 `FirstChangeToHomeCallback` 和 `LoginMainPageContext SetupView`，未执行登录或接受协议。带边框窗口的实际客户区高度为 0，反复出现 `RenderTextureDesc height must be greater than zero`；约 63 秒因 swap 增长保护主动关闭，清理无残留。日志为 `genshin-hadron-one-instruction-*`。这支持 Home 等待与暂停检查点有关，尚不构成正常显示/稳定运行验收。
- MacNeutron 的 Logo 崩溃跟踪定位到原生 `ntdll` 的 `memset` 写入无效地址 `8888866666000003`，大小 `0x4d0` 与 ARM64EC context 大小相符。仍需追踪 context 指针来源。更早的 `MHYPBase +0x680003` VMCALL 异常有游戏自己的处理记录，不能将它直接认作根因。

### 窗口模式

Wine 的游戏全屏不等同于 macOS 原生全屏，也不保证创建独立 Space。测试入口在隔离 prefix 中复用 YAAGL 的分辨率注册表设置：1280×720、fullscreen=0；设置 Wine Mac Driver 的 `WindowsFloatWhenInactive=none`、`CaptureDisplaysForFullscreen=N`，关闭失焦置顶和显示器独占。

带边框模式在本机得到客户区 `1280×0`、外框高度 `32767`。普通 D3D11 最小程序的窗口和 caption 指标正常，问题尚未证明属于通用 Wine 窗口实现。追加 Unity Windows Player 的 [`-popupwindow`](https://docs.unity3d.com/2022.3/Documentation/Manual/PlayerCommandLineArguments.html) 后，游戏 API 返回无边框 `1280×720`、exstyle=0；测试入口保留该参数。100 秒及追加 150 秒窗口实验记录到 `LoginMainPageContext SetupView`，未再出现 RenderTextureDesc 高度错误，没有自行退出；150 秒一轮在 60/95/125 秒均检查到 1280×720 和 `WM_NULL` 响应成功，结束后清理无残留。RSS 峰值约 2.1 GiB、swap 增长峰值约 500 MiB。记录为 `genshin-hadron-popup-one-instruction-*` / `genshin-hadron-popup-verify-*`，使用 `FEX_MULTIBLOCK=0` / `FEX_MAXINST=1`。独立 Tester 已核对日志及无残留；尚缺直接游戏画面和完整前台切换证据，不能把 Windows API 响应当成完整 UI 验收。

修改后的 JIT 实验统一关闭 FEX 磁盘缓存，避免复用同一源码 hash 对应的旧编译缓存。已提交的最小 C 探针和局部补丁保存在 `arm64-experiments/`；额外本机诊断命令留在 `.arm64-build/tools`，不会改动生产 prefix。Hadron 的 probe 也固定使用 `FEX_MULTIBLOCK=0` / `FEX_MAXINST=1`；这会增加 JIT 开销，不能当成性能优化或正式发行配置。

[FEX 的 Unity/.NET ARM64EC 讨论](https://github.com/FEX-Emu/FEX/issues/6014)也记录了完整 SMC 检查下从崩溃变为挂起的情况，属于后续诊断线索；不能据此认定本机原神的根因相同。线程暂停已形成最小复现；后续核对真实画面/前台切换并降低诊断配置开销，再追踪 MacNeutron 的无效上下文指针。只有真实画面及未登录正常运行完成验收后，才接入启动器的原生运行时选项和配套 DXMT。

## 已提交的实验材料

- [`gs-selector.c`](../arm64-experiments/gs-selector.c)：selector 0/0x2b 写入、读回、恢复及 GS:0x30 TEB 地址检查；失败退出非零。
- [`thread-context.c`](../arm64-experiments/thread-context.c)：阻塞等待与纯计算线程各 20 次 Suspend/GetThreadContext/Resume，检查 RIP/RSP 非零。默认 FEX 配置会卡住，运行时必须另设时限并关闭该隔离 prefix 的 wineserver。
- [`window-probe.c`](../arm64-experiments/window-probe.c)：只读枚举默认 Windows 桌面，筛选 YuanShen.exe，输出客户区/外框尺寸、样式和 WM_NULL 响应。退出 0 仅代表枚举调用成功，须核对每行结果。
- [`fex-gs-selector.patch`](../arm64-experiments/fex-gs-selector.patch)：本地候选差异，应用于固定 FEX `0df84d3` 加上 Hadron v0.2.0 的五项 FEX 补丁后的源码。未向 FEX 上游提交，也未默认接入启动器。

以上源码沿用本机实际诊断，不包含游戏、prefix、账号数据或运行时二进制。用本机固定编译器复现：

```sh
task_toolchain="$PWD/.arm64-build/toolchain/llvm-mingw-20260922-ucrt-macos-universal/bin"
"$task_toolchain/x86_64-w64-mingw32-clang" -static -fms-extensions \
  arm64-experiments/gs-selector.c -o .arm64-build/tests/gs-selector.exe
/opt/homebrew/bin/x86_64-w64-mingw32-gcc -static \
  arm64-experiments/thread-context.c -o .arm64-build/tests/thread-context-trace.exe
"$task_toolchain/x86_64-w64-mingw32-clang" -static \
  arm64-experiments/window-probe.c -o .arm64-build/tests/default-window.exe
```

游戏副本、两套运行时、已编译候选库和原始日志仍在被 Git 忽略的 `.arm64-build`。克隆仓库不会自动具备这些材料；须先按本记录准备，脚本会拒绝缺失组件或仍在运行的实验实例。这里提交的是阶段成果及复现源码，尚无原生运行时发行安装器。

## 有界复现入口

完成上述本机准备后：

```sh
sophon_server/.venv/bin/python probe-arm64-game.py hadron
sophon_server/.venv/bin/python probe-arm64-game.py macneutron
```

脚本只指向固定的实验 prefix 和克隆游戏，以 1280×720 无边框窗口启动。默认 120 秒，允许 `--seconds 1..300`；低进程优先级、30 FPS，超过 6 GiB RSS、关键内存压力或新增 1 GiB swap 时关闭。使用已有 Sophon 的 psutil，不引入依赖。结束或中断时关闭该 prefix 的 wineserver；若仍有该独占实验运行时的客户端，则逐个终止，保存日志、内存和清理记录。退出 0 仅表示观察时限完成，不代表画面正常或游戏验收通过。

同一实验运行时已有进程时脚本拒绝启动；不要与另一个实验并行运行。启动器 UI 测试还需避开固定的 6868 下载端口。完成后必须核对进程已退出。
