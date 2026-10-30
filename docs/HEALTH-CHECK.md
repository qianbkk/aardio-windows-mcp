# 健康检查报告 (Health Check)

**生成时间**: 2026-08-12 03:45 (kilo 全面检修后重新生成)

## 1. aardio 环境
- [OK] aardio IDE: D:\APPALL\aardio\aardio.exe (6.2 MB)
- [OK] lib 目录: 49 个分类

## 2. 扩展库结论 (重大更正)
- **[OK] 不需要装任何扩展库** — 之前文档说"9 个扩展库要装"是错误结论
- 实测: `com`/`gdip.bitmap`/`win.clip.bitmap`/`key`/`win.util.popup`/`inet.http`/`inet.url`/`fsys.log`/`wsock.tcp.simpleHttpServer` 全部在标准库 `lib/` 下
- 真正不存在的: `registry` (有 util.registry 但那是对象引用管理器, 不是注册表 API)、`keyboard`
  - keyboard 用 `key` 库替代 (sendString/combine 同 API)
  - registry 端点已删除 (2 个)

## 3. main.aardio 源码状态
- [OK] `projects/00-rpc-server/main.aardio` (16981 bytes, 03:41) — 已修复 ~24 处 API 错误
- [OK] tools 副本 + IDE 备份已同步 (03:39)
- [FAIL] `dist/rpc-server.exe` (03:00:57) — **旧版, 启动即死, 必须 F7 重发**

## 4. 端点实测 (scripts/test-all-endpoints.ps1, 旧 EXE)
- [FAIL] 15/15 FAIL — 旧 EXE 启动后不监听 8765, 全部连接拒绝
- 修复后源码未发布, 无法实测新端点

## 5. 30 个 GUI 工具 import 验证
- [OK] 32 个 .aardio 文件全部 import 对照 lib 验证通过 (含 builtin)
- 修复 9 处: preg×2, fsys.dir×5, fsys.search×1, text.markdown×1 (涉及 02/05/09/11/13/22/23)
- [TODO] 尚未逐个 F5 运行时验证

## 6. 待办
- [ ] **F7 重新发布 EXE** (aardio IDE 已打开工程)
- [ ] 跑测试脚本 → 期望 15/15 PASS
- [ ] 30 个工具逐个 F5 运行时验证
