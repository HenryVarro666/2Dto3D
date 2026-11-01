# CI-001：GitHub前端异步查看器等待失败

客户端日期2026-11-01；失败工作流为 `Check workbench`，不是模型评测。修复在独立worktree `.worktrees/ci-async-editor`、分支 `fix/ci-async-editor` 中进行，起点为远端main的8253f36；当前光伏识别分支E07与另一聊天的去畸变实验工作区不改。

## 失败依据与原因

- [main / 8253f36 / run41277276181](https://github.com/HenryVarro666/2Dto3D/actions/runs/41277276181)：后台与Ruff通过，前端 `App.i18n.test.tsx` 与 `MultiviewWorkbench.test.tsx` 等待按钮启用失败，66/68通过。
- [测量分支 / 7a4038a / run41281204159](https://github.com/HenryVarro666/2Dto3D/actions/runs/41281204159)：后台/Ruff通过，前端多视角同一断言失败，69/70通过。
- [测量分支 / b58b72d / run41281382018](https://github.com/HenryVarro666/2Dto3D/actions/runs/41281382018)同样失败；保留原日志，不用重跑绿灯覆盖失败历史。
- 失败断言是 `expect(button).toBeEnabled()`。真实查看器经React.lazy载入Three.js；工作台在准备阶段锁定，jsdom没有WebGL，真实查看器载入后才触发错误回调并释放锁。Testing Library默认异步等待为1秒，首次冷转换/加载可以超过该时间。本机缓存较热，普通测试通过不能证明GitHub冷启动可靠。

## 复现与改进

本机ignored证据目录：`data/ci/2026-11-01-async-viewer/`（位于canonical项目根目录，worktree中不复制原始资料）。

- 在独立诊断Vite配置中只对真实 `SceneViewer.tsx` 转换增加延迟，不替换组件或API，不修改生产代码。1.6秒延迟已复现多视角原断言失败。
- 最初i18n对照没有失败：Vitest5默认持久化模块转换缓存，后续运行跳过转换钩子，不能把它当冷启动对照。保留通过日志；冷启动诊断随后显式关闭 `fsModuleCache` 并记录钩子start/end。
- 编辑流程测试在开始计时前静态载入真实查看器。继续运行真实WebGL失败回调、进度、三语、编辑/隐藏/归属、保存与单图模式断言。不会假装3D载入成功，不增加全局等待时间，不跳过失败用例。
- 单图/多图共四个编辑流程测试文件使用相同初始化方式；生产懒加载、队列、模型、测量、依赖锁及Actions检查命令保持原样。

## 验证与同步

本机初步验证：关闭转换缓存、真实查看器冷转换延迟2.4秒，两处原断言均先RED；预载入后两者GREEN。使用与失败CI相同的Node22.23.4，68前端全套（转换缓存关闭）、119后端＋2项可选ML跳过、构建/Ruff/diff通过。随后远端main更新为cf98129；将同一小补丁rebase到该提交，未修改另一个聊天的工作树或测量代码。最新主线本机完整检查为131后端通过、2项可选ML跳过，70前端通过（Node22.23.4、模块转换缓存关闭），TypeScript/Vite构建、Ruff、8SVG及diff检查通过。GitHub验证待随后追加。

保留失败日志、诊断配置、修复后输出与GitHub运行链接。没有运行光伏照片或VGGT，不能把CI通过当灰线/圆管/背景泛柜的质量改善。
