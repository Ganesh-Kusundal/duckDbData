#!/usr/bin/env python
"""
Setup script for DuckDB Financial SDK
"""

from setuptools import setup, find_packages
import os

# Read version from __init__.py
def get_version():
    init_file = os.path.join(os.path.dirname(__file__), 'duckdb_financial_sdk', '__init__.py')
    with open(init_file, 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"\'')
    return '1.0.0'

# Read README
def get_long_description():
    readme_file = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_file):
        with open(readme_file, 'r') as f:
            return f.read()
    return ''

setup(
    name='duckdb-financial-sdk',
    version=get_version(),
    description='Python SDK for DuckDB Financial Infrastructure API',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    author='Financial Data Team',
    author_email='team@example.com',
    url='https://github.com/your-org/duckdb-financial-infra',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Office/Business :: Financial :: Investment',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='duckdb financial trading api sdk market-data',
    python_requires='>=3.8',
    install_requires=[
        'requests>=2.25.0',
        'websockets>=10.0',
        'asyncio-mqtt>=0.11.0',  # For MQTT support if needed
        'pydantic>=2.0.0',      # For data validation
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'black>=22.0.0',
            'isort>=5.10.0',
            'mypy>=1.0.0',
            'sphinx>=5.0.0',    # For documentation
        ],
        'examples': [
            'pandas>=1.3.0',
            'matplotlib>=3.5.0',
            'plotly>=5.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'duckdb-financial-client = duckdb_financial_sdk.cli:main',
        ],
    },
    project_urls={
        'Documentation': 'https://duckdb-financial-sdk.readthedocs.io/',
        'Source': 'https://github.com/your-org/duckdb-financial-infra',
        'Tracker': 'https://github.com/your-org/duckdb-financial-infra/issues',
    },
)
