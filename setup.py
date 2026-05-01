from setuptools import setup, find_packages

setup(
    name="clouds-everywhere",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["requests"],
    author="Your Name",
    description="Check satellite image availability by cloud coverage",
)