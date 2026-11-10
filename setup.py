from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="coc-farming-controller",
    version="1.0.0",
    author="CoC Automation Team",
    description="Autonomous Vision-Based AI Farming Controller for Clash of Clans on Windows PC",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Games/Entertainment :: Real Time Strategy",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "coc-farm=src.app.main:main",
        ],
    },
    include_package_data=True,
)
