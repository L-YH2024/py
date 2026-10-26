# 系统设计文档

## ER 关系

`User 1:N Survey 1:N Question 1:N Option`；`Survey 1:N Response 1:N Answer`；`Answer` 可关联一个 `Option`，也可保存填空文本。

## 核心流程

创建者登录 → 创建问卷和题目 → 生成 public_id 填写链接 → 匿名用户填写 → 服务端校验必填和防重复 → 保存 Response/Answer → SQL 聚合 → ECharts 展示或 CSV 导出。

## 关键设计

IP 只保存 SHA-256 哈希，Cookie 保存随机 visitor token；问卷截止和关闭状态由服务端校验。统计按题目和选项实时查询，避免缓存导致结果过期。
