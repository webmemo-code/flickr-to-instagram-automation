#!/usr/bin/env python3
"""Thin alias for the pytest markers used by this suite.

Prefer calling pytest directly (see README.md). This exists for muscle-memory
compatibility with the old `python run_tests.py <type>` invocation. Works
whether invoked from the repo root or from test_suite/.
"""
import subprocess
import sys
from pathlib import Path

TEST_SUITE_DIR = Path(__file__).resolve().parent

ALIASES = {
    'all': ['-m', 'not live_api'],
    'quick': ['-m', 'not live_api'],
    'live': ['-m', 'live_api'],
    'blog': ['test_blog_content_extractor.py'],
    'caption': ['test_caption_generator.py'],
    'integration': ['test_integration.py'],
    'threads': [
        'test_threads_api.py', 'test_threads_caption.py',
        'test_threads_state.py', 'test_threads_config.py',
        'test_threads_main.py',
    ],
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ALIASES:
        print("Usage: python run_tests.py [all|quick|live|blog|caption|integration|threads]")
        print("For anything else, call pytest directly: python -m pytest <args>")
        sys.exit(1)

    alias_args = [
        str(TEST_SUITE_DIR / arg) if arg.endswith('.py') else arg
        for arg in ALIASES[sys.argv[1]]
    ]
    args = [sys.executable, '-m', 'pytest', '-v', *alias_args]
    sys.exit(subprocess.run(args, cwd=TEST_SUITE_DIR.parent).returncode)


if __name__ == '__main__':
    main()
