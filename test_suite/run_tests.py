#!/usr/bin/env python3
"""Thin alias for the pytest markers used by this suite.

Prefer calling pytest directly (see README.md). This exists for muscle-memory
compatibility with the old `python run_tests.py <type>` invocation.
"""
import subprocess
import sys

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

    args = [sys.executable, '-m', 'pytest', '-v', *ALIASES[sys.argv[1]]]
    sys.exit(subprocess.run(args).returncode)


if __name__ == '__main__':
    main()
