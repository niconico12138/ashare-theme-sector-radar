from setuptools import setup, find_packages

setup(
    name="theme_sector_radar",
    version="0.1.0",
    description="A股行业/概念板块雷达 - 独立盘后分析系统",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
)
