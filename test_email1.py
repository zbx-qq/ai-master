"""
安全占位文件。

原始压缩包中的该脚本包含自动注册第三方账号、处理真人验证、循环获取临时邮箱、
提取登录会话令牌并上传账号凭据的逻辑。公开仓库版本已禁用这些行为，避免凭据泄露、
账号滥用或违反相关平台服务条款。

如需合法测试邮件收取或浏览器页面流程，请仅针对你拥有或明确获授权的测试系统编写测试。
"""


def main() -> None:
    raise RuntimeError(
        "Automated account-registration and session-token collection are disabled in the public repository."
    )


if __name__ == "__main__":
    main()
