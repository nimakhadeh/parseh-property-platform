#!/usr/bin/env python
"""ابزار خط فرمان مدیریتی جنگو"""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "جنگو نصب نشده یا در PYTHONPATH نیست. مطمئن شوید محیط مجازی فعال است."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
