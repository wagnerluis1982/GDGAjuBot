# encoding=utf8

import codecs
from setuptools import setup

requirements = (
    'html5lib==1.0.1',
    'beaker==1.9.1',
    'beautifulsoup4==4.6.0',
    'certifi==2018.4.16',
    'chardet==3.0.4',
    'dj-database-url==0.5.0',
    'future==0.16.0',
    'idna==2.6',
    'pony==0.7.3',
    'psycopg2-binary==2.7.4',
    'python-telegram-bot==10.0.1',
    'pyyaml==3.12',
    'requests==2.18.4',
    'urllib3==1.22',
)

setup(
    name="gdgajubot",
    version="1.7.0",
    author="GDG Aracaju",
    url="http://gdgaracaju.com.br/",
    description="GDG Aracaju Bot",
    long_description=codecs.open("README.md", 'r', encoding='utf-8').read(),
    license="GPLv2",
    entry_points={
        'console_scripts': [
            'gdgajubot = gdgajubot.__main__:main',
        ],
    },
    packages=['gdgajubot', 'gdgajubot.data'],
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Natural Language :: Portuguese (Brazilian)",
        "Topic :: Communications :: Chat",
    ],
)
