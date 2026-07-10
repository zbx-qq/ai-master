# ChatGPT 事件流系统设计

## 概述

项目通过 Playwright 监听对话请求的 Server-Sent Events（SSE）响应，并保存原始响应体供后续解析。

## 主要事件

- `delta_encoding`：协议版本或恢复元数据。
- `delta`：增量内容、消息状态和工具调用信息。
- `[DONE]`：流结束标记。

## 处理流程

1. 浏览器页面发起对话请求。
2. `response` 事件处理器筛选 `backend-api/f/conversation`。
3. 保存 URL、请求 payload、响应 body 和时间戳。
4. SSE 解析器逐行识别 `event:` 与 `data:`。
5. JSON 数据反序列化并按顺序组合。
6. 调度器把原始结果提交给已配置的后端 API。

## 安全要求

- 不在日志或仓库中保存真实 Cookie、恢复令牌或 API Key。
- 生产环境应限制接口访问、启用 HTTPS 并进行日志脱敏。
- 仅对拥有或明确获授权的系统运行自动化测试。
