from setuptools import setup, find_packages

setup(
    name         = "shift-parser",
    version      = "1.0.0",
    description  = "Parse shift-scheduling emails using any LLM provider",
    packages     = find_packages(),
    python_requires = ">=3.10",
    install_requires = [
        "openai>=1.0.0",
    ],
    extras_require = {
        "dev": ["pytest"],
    },
    entry_points = {
        "console_scripts": [
            "shift-parser=shift_parser.__main__:main",
        ],
    },
)
