"""Setup configuration for IAVideoEditor."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="iavideoeditor",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python-based video editing application",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/iavideoeditor",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.12.0",
            "flake8>=3.9.0",
            "pylint>=2.9.0",
            "black>=21.0",
            "mypy>=0.910",
        ],
    },
)
