# 2026-10-27 · 通用系统镜像工作站入口

用户确定该网站将跨项目使用；已去除 Yikai 专用品牌，增加项目归属/筛选，保留 Yikai 为首个已验证配置。
本次在 Edge 真实在线页面验证：NAS 在线、两版镜像可见、项目筛选值可切换、系统盘不可选择、原任务记录保留。

- `live-state.json`：2026-10-27 现场 API 快照，带采集时间；可供 `--preview-state` 只读展示。
- `webui-generic.jpg`：实际在线页面截图。
- 33 项无物理盘测试通过；包含未适配 profile 拒绝恢复、预览模式拒绝写入且不调用设备枚举。
- 工作站仍使用既有部署路径、服务名和 NAS 目录，未搬移镜像。

内存选型决定及平台边界：[docs/12-decisions-20261027.md](../../docs/12-decisions-20261027.md)。
harness=codex；model=unknown；native session `01a1678d-3bfb-75b0-964e-4b2dc0a3a6a9`；host `Yuntians-MacBook-Pro.local`；baseline `f72ef48e02a10a0c1547c435d01657ebda289f5e`。
