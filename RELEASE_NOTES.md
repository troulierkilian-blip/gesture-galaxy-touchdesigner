# v1.0.0 — Gesture Galaxy TouchDesigner

首次公开发布：手势控制的三维银河，包含增厚盘面、暖白椭球银心、四条主旋臂、短分支、暗尘带和八个环绕星团。

- 手掌相对拖动旋转，竖拇指切换旋转与移动，双手缩放。
- 握拳聚合、张掌扩散、捏合增亮、V 手势切色，支持左手接管及鼠标模拟。
- 默认 720p、20,000 星点、640×360/16 步程序化体积星云。
- 提供主工程、可重建源码、中文面板、固定版本依赖下载器、30 项逻辑测试及精选截图。
- 历史测量（2026-10-23，RTX 3060 Laptop 6GB）：600.02 秒，平均58.97 FPS、最低52.17 FPS。增强版真人反馈仍待确认。

## 首次使用

1. 解压整个 ZIP。
2. 安装并激活 TouchDesigner；实测版本2025.33230 Non-Commercial。
3. 运行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-Dependencies.ps1`。
4. 双击 `Start-GestureParticles.cmd`。

TouchDesigner、模型和约188 MB的上游插件不打入 ZIP；插件由下载器校验后安装。新增代码采用MIT，第三方许可单独保留。

ZIP附有独立SHA-256校验文件；`FILE-MANIFEST.json`列出包内公开文件的哈希。
