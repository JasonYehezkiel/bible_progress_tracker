from setuptools import setup, find_packages

setup(
    name="bible_ref_pkg",
    version="0.1.0",
    description="A package for Bible reading recap using NLP",
    author="Jason Yehezkiel Wijaya",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pandas>=3.0.0",
        "numpy>=2.4.2",
        "RapidFuzz>=3.14.3"
    ]
)