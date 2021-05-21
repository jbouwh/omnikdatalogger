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


with open("README.md", "r", encoding="UTF-8") as fh:
    long_description = fh.read()

install_requires = [
    'configparser>=3.7.4',
    'requests>=2.21.0',
    'cachetools>=3.1.1',
    'pytz>=2019.1',
    'paho-mqtt>=1.5.0',
    'dsmr-parser>=0.21',
    'astral>=1.10.1',
    'pyyaml>=5.1',
]

setup(
    name="omnikdatalogger",
    version=get_version('apps/omnikdatalogger/omnik'),
    license="gpl-3.0",
    author="Jan Bouwhuis",
    author_email="jan@jbsoft.nl",
    description="Omnik Data Logger",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jbouwh/omnikdatalogger",
    package_dir={"": "apps/omnikdatalogger"},
    packages=find_packages(where="apps/omnikdatalogger"),
    data_files=[('share/omnikdatalogger', [
        'apps/omnikdatalogger/data_fields.json',
        'scripts/systemd/omnikdatalogger.service',
        ])
                ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Topic :: Home Automation',
        'Programming Language :: Python :: 3.7',
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent"
    ],
    install_requires=install_requires,
    scripts=['apps/omnikdatalogger/omniklogger.py'],
)
