import os
import sys

from setuptools import find_packages, setup

rootpath = os.path.abspath(os.path.dirname(__file__))


# Extract version
def extract_version(module='kyoukai'):
    version = None
    fname = os.path.join(rootpath, module, 'app.py')
    with open(fname) as f:
        for line in f:
            if line.startswith('__version__'):
                _, version = line.split('=')
                version = version.strip()[1:-1]  # Remove quotation characters.
                break
    return version


deps = [
    "httptools>=0.0.9,<0.1.0",
    "asphalt>=2.1.1,!=3.0.0",
    "werkzeug>=0.12.0,<0.13.0",
    "h2>=3.0.0,<3.1.0",
]

setup(
    name='Kyoukai',
    version=extract_version(),
    packages=[
        'kyoukai',
        'kyoukai.backends',

        # ext packages
        'kyoukai.ext',
        'kyoukai.ext.rest',
    ],
    url='https://mirai.veriny.tf',
    license='MIT',
    author='Laura Dickinson',
    author_email='l@veriny.tf',
    description='A fast, asynchronous web framework for Python 3.5+',
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5"
        "Programming Language :: Python :: 3.6",
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
        "gunicorn": ["aiohttp>=2.2.0,<2.3.0", "gunicorn>=19.6.0"],
        "uwsgi": ["greenlet>=0.4.0"]
    }
)
