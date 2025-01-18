"""
Setup file for Agent360 package.
"""
from setuptools import setup, find_packages

setup(
    name="agent360",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "pydantic>=2.4.2",
        "python-jose>=3.3.0",
        "passlib>=1.7.4",
        "redis>=5.0.1",
        "cassandra-driver>=3.29.0",
        "pytest>=7.4.3",
        "pytest-asyncio>=0.21.1",
        "pytest-cov>=4.1.0",
        "httpx>=0.25.0",
        "python-multipart>=0.0.6",
        "aiohttp>=3.9.1",
        "opentelemetry-api>=1.20.0",
        "opentelemetry-sdk>=1.20.0",
        "opentelemetry-instrumentation-fastapi>=0.41b0",
    ],
    extras_require={
        "dev": [
            "black>=23.10.0",
            "isort>=5.12.0",
            "mypy>=1.6.1",
            "pylint>=3.0.2",
            "pytest-mock>=3.12.0",
        ]
    },
    python_requires=">=3.11",
)
