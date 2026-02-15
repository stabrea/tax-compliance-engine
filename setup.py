"""Package setup for Tax Compliance Engine."""

from setuptools import setup, find_packages

setup(
    name="tax-compliance-engine",
    version="1.0.0",
    author="Taofik Bishi",
    description="Sales tax compliance automation for multi-state businesses",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/taofikbishi/tax-compliance-engine",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "rich>=13.0",
        "pandas>=2.0",
    ],
    entry_points={
        "console_scripts": [
            "tax-engine=tax_engine.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Accounting",
    ],
    keywords="sales-tax compliance automation nexus refund multi-state",
)
