# ai-master

基于 FastAPI 与 Playwright 的自动化任务项目。

## 安全说明

本仓库上传前已移除压缩包中的真实 Cookie、API Key 和账号密码：

- 本地环境变量请参考 `.env.example`
- Cookie 示例请参考 `cs.example.json`
- 不要提交 `.env`、`cs.json` 或其他真实凭据

## 基本使用

```bash
conda env create -f environment.yml
conda activate gptAutoCrawling
playwright install chromium
python main.py
```

调度器：

```bash
python scheduler.py
```

请仅在获得授权并符合相关网站服务条款及当地法律的情况下使用浏览器自动化功能。
