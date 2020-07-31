import os
import re
from setuptools import setup, find_packages


def get_version(package):
    """
    Return package version as listed in `__version__` in `__init__.py`.
    """
    path = os.path.join(os.path.dirname(__file__), package, 'omnikloggerproxy.py')
    with open(path, 'rb') as f:
        init_py = f.read().decode('utf-8')
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


with open("scripts/proxy/README.md", "r", encoding="UTF-8") as fh:
    long_description = fh.read()

install_requires = [
    'configparser>=3.7.4',
    'pyyaml>=5.1',
    'requests>=2.21.0',
    'cachetools>=3.1.1',
    'paho-mqtt>=1.5.0',
]

setup(
    name="omnikdataloggerproxy",
    version=get_version('scripts/proxy'),
    license="gpl-3.0",
    author="Jan Bouwhuis",
    author_email="jan@jbsoft.nl",
    description="Omnik Data Logger Proxy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jbouwh/omnikdatalogger",
    package_dir={"": "scripts/proxy"},
    packages=find_packages(where="scripts/proxy"),
    data_files=[('share/omnikdatalogger', [
        'scripts/proxy/iptables_setup_example.sh',
        'scripts/proxy/omnikproxy_example_startup.sh'])
                ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Topic :: Home Automation',
        'Programming Language :: Python :: 3.5',
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    install_requires=install_requires,
    scripts=['scripts/proxy/omnikloggerproxy.py'],
)
