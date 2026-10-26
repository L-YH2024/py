# Debug 日志

## 2026-10-26

- 问题：Excel 打开 CSV 中文乱码。
  - 原因：普通 UTF-8 CSV 缺少 BOM。
  - 修复：导出内容前增加 UTF-8 BOM（`\\ufeff`）。
- 问题：匿名填写需要识别重复提交。
  - 修复：使用 IP SHA-256 哈希与随机 Cookie token 组合，并建立问卷级唯一约束。
