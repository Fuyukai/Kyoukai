import os
import sys

from setuptools import find_packages, setup

rootpath = os.path.abspath(os.path.dirname(__file__))


# Extract version
def extract_version(module = 'kyoukai'):
    version = None
    fname = os.path.join(rootpath, module, 'app.py')
    with open(fname) as f:
        for line in f:
            if line.startswith('VERSION'):
                _, version = line.split('=')
                version = version.strip()[1:-1]  # Remove quotation characters.
                break
    return version


deps = [
    "httptools>=0.0.9",
    "asphalt>=2.0.0",
    "werkzeug>=0.11.10",
]

setup(
    name='Kyoukai',
    version=extract_version(),
    packages=find_packages(),
    url='https://mirai.veriny.tf',
    license='MIT',
    author='Isaac Dickinson',
    author_email='sun@veriny.tf',
    description='A fast, asynchronous web framework for Python 3.5+',
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Application Frameworks"
    ],
    install_requires=deps,
    test_requires=[
        "pytest",
        "pytest-asyncio"
    ],
    extras_require={
        "gunicorn": ["aiohttp>=1.1.0", "gunicorn>=19.6.0"],
        "http2": ["h2>=2.5.0"],
        "uwsgi": ["greenlet>=0.4.0"]
    }
)
