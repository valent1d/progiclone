# setup.py

from setuptools import setup, find_packages
from progiclone import __version__

setup(
    name="progiclone",
    version=__version__,
    author="VLTN x Progiseize",
    author_email="v.denis@progiseize.fr",
    description="Outil d'anonymisation des données sécurisé pour Dolibarr",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/valent1d/progiclone",
    packages=find_packages(),
    install_requires=[
        'pyfiglet',
        'tqdm',
        'Faker',
        'mysql-connector-python',
        'requests',
        'PyYAML',  # Pour le support des fichiers de configuration YAML
        'argparse',  # Pour le parsing des arguments en ligne de commande
        'sshtunnel',  # Pour le support du tunnel SSH
    ],
    entry_points={
        "console_scripts": [
            "progiclone=progiclone.main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Database",
        "Topic :: Security",
        "Topic :: Utilities",
    ],
    python_requires='>=3.7',
    package_data={
        'progiclone': ['example-config.yml'],
    },
    include_package_data=True,
    keywords='dolibarr anonymization database mysql ssh security gdpr',
)
