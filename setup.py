from setuptools import setup, find_packages

setup(
    name="trex-expense-splitter",
    version="0.1.0",
    description="🧳 Tour Expense Splitter — track group trip expenses, split by person, auto-settle who owes whom",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="S M Al Hasib",
    author_email="alhasibsm@gmail.com",
    url="https://github.com/alhasbsm/trex-expense-splitter",
    project_urls={
        "Source": "https://github.com/alhasbsm/trex-expense-splitter",
    },
    packages=find_packages(),
    install_requires=[
        "click>=8.0",
        "tabulate>=0.9",
        "rich>=13.0",
    ],
    entry_points={
        "console_scripts": [
            "trex=tourexpenses.cli:cli",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Accounting",
        "Topic :: Utilities",
    ],
    keywords="expense splitter trip travel group settlement splitwise cli",
    license="MIT",
)
