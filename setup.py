import os
import re
from setuptools import setup, find_packages

def get_version(package):
    """
    Return package version as listed in `__version__` in `__init__.py`.
    """
    path = os.path.join(os.path.dirname(__file__), package, '__init__.py')
    with open(path, 'rb') as f:
        init_py = f.read().decode('utf-8')
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="omnik-data-logger",
    version=get_version('omnik'),
    author="Pascal Prins",
    author_email="pascal.prins@foobar-it.com",
    description="Omnik data logger",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pprins/omnik-data-logger",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires = [
        "requests"
    ],
    scripts=['bin/omnik-logger'],
)