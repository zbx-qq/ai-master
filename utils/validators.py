# utils/validators.py
"""数据验证工具"""

import re
from typing import Any

from utils.exceptions import ValidationException


class RequestValidator:
    """请求数据验证器"""

    @staticmethod
    def validate_problems(problems: list[str]) -> None:
        """验证问题列表"""
        if not problems:
            raise ValidationException("问题列表不能为空", "EMPTY_PROBLEMS")

        if len(problems) > 10:
            raise ValidationException(
                "单次请求问题数量不能超过10个", "TOO_MANY_PROBLEMS"
            )

        for i, problem in enumerate(problems):
            if not isinstance(problem, str):
                raise ValidationException(
                    f"问题 {i + 1} 必须是字符串类型", "INVALID_PROBLEM_TYPE"
                )

            if not problem.strip():
                raise ValidationException(f"问题 {i + 1} 不能为空", "EMPTY_PROBLEM")

            if len(problem) > 1000:
                raise ValidationException(
                    f"问题 {i + 1} 长度不能超过1000字符", "PROBLEM_TOO_LONG"
                )

    @staticmethod
    def validate_cookies(cookies: list[dict[str, Any]]) -> None:
        """验证Cookie数据"""
        if not cookies:
            raise ValidationException("Cookie数据不能为空", "EMPTY_COOKIES")

        required_fields = ["name", "value", "domain", "path"]

        for i, cookie in enumerate(cookies):
            if not isinstance(cookie, dict):
                raise ValidationException(
                    f"Cookie {i + 1} 必须是字典类型", "INVALID_COOKIE_TYPE"
                )

            for field in required_fields:
                if field not in cookie:
                    raise ValidationException(
                        f"Cookie {i + 1} 缺少必需字段: {field}", "MISSING_COOKIE_FIELD"
                    )

                if not isinstance(cookie[field], str) or not cookie[field].strip():
                    raise ValidationException(
                        f"Cookie {i + 1} 的 {field} 字段不能为空", "EMPTY_COOKIE_FIELD"
                    )

    @staticmethod
    def validate_click_parameter(click: Any) -> None:
        """验证点击参数"""
        if not isinstance(click, bool):
            raise ValidationException("click参数必须是布尔类型", "INVALID_CLICK_TYPE")


class CookieValidator:
    """Cookie验证器"""

    @staticmethod
    def is_valid_domain(domain: str) -> bool:
        """验证域名格式"""
        domain_pattern = r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$"
        return bool(re.match(domain_pattern, domain.lstrip(".")))

    @staticmethod
    def normalize_cookie_for_playwright(cookie: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize cookie for Playwright's add_cookies method

        Automatically sets required fields based on cookie name and properties:
        - Cookies with __Secure- prefix require secure=True
        - Cookies with __Host- prefix require secure=True, path=/, and no domain
        - Sets sensible defaults for missing optional fields
        """
        normalized = cookie.copy()

        cookie_name = normalized.get("name", "")
        if cookie_name.startswith("__Secure-"):
            normalized["secure"] = True
        elif cookie_name.startswith("__Host-"):
            normalized["secure"] = True
            normalized["path"] = "/"
            if "domain" in normalized:
                del normalized["domain"]

        domain = normalized.get("domain", "")
        if "secure" not in normalized or normalized["secure"] is None:
            if domain.endswith("chatgpt.com") or domain.endswith("openai.com"):
                normalized["secure"] = True
            else:
                normalized["secure"] = False

        if "httpOnly" not in normalized or normalized["httpOnly"] is None:
            normalized["httpOnly"] = False

        if "sameSite" not in normalized or normalized["sameSite"] is None:
            normalized["sameSite"] = "None" if normalized.get("secure") else "Lax"

        return normalized

    @staticmethod
    def validate_cookie_security(cookie: dict[str, Any]) -> list[str]:
        """验证Cookie安全性，返回警告列表"""
        warnings = []

        if not cookie.get("domain", "").endswith("chatgpt.com"):
            warnings.append("Cookie域名可能不正确，建议使用ChatGPT相关域名")

        if "value" in cookie and len(cookie["value"]) < 10:
            warnings.append("Cookie值可能无效或已过期")

        return warnings
