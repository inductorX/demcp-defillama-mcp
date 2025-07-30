#!/usr/bin/env python3
"""
Setup script for DefiLlama MCP Server
"""

from setuptools import setup, find_packages

# Read the README file for long description
try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "DefiLlama MCP Server - Access DeFi data through Model Context Protocol"

# Read requirements from requirements.txt
try:
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        requirements = [
            line.strip()
            for line in fh.readlines()
            if line.strip() and not line.startswith("#")
        ]
except FileNotFoundError:
    requirements = ["mcp>=1.0.0", "httpx>=0.24.0"]

setup(
    name="defillama-mcp-server",
    version="1.0.0",
    author="bhanusanghi",
    author_email="bhanussanghi@gmail.com",
    description="Model Context Protocol server for DefiLlama DeFi data APIs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bhanusanghi/Defillama-mcp",
    py_modules=["defillama_mcp_server"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Office/Business :: Financial",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "defillama-mcp=defillama_mcp_server:main",
        ],
    },
    keywords="defi, llama, mcp, model-context-protocol, ai, blockchain, cryptocurrency, yield-farming",
    project_urls={
        "Bug Reports": "https://github.com/bhanusanghi/Defillama-mcp/issues",
        "Source": "https://github.com/bhanusanghi/Defillama-mcp",
        "Documentation": "https://github.com/bhanusanghi/Defillama-mcp#readme",
        "DefiLlama": "https://defillama.com/",
        "MCP Protocol": "https://modelcontextprotocol.io/",
    },
    include_package_data=True,
    zip_safe=False,
)