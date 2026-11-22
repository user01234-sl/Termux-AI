from pathlib import Path
from setuptools import setup, find_packages

ROOT = Path(__file__).parent

requirements = [
    line.strip()
    for line in (ROOT / "requirements.txt").read_text().splitlines()
    if line.strip() and not line.strip().startswith("#")
]

setup(
    name="termuxai",
    version="0.4.4",
    description="An AI client for Termux",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "termuxai=termuxai.app:run",
        ],
    },
    python_requires=">=3.10",
)