# encoding=utf8

import codecs
from setuptools import setup

setup(
    name = "gdgajubot",
    version = "1.4",
    author = "GDG Aracaju",
    url = "http://site.gdgaracaju.com.br/",
    description = "GDG Aracaju Bot",
    long_description = codecs.open("README.md", 'r', encoding='utf-8').read(),
    license = "GPLv2",
    packages = ["gdgajubot"],
    scripts = ['scripts/gdgajubot'],
    install_requires=[
        "Beaker==1.8.0",
        "beautifulsoup4==4.4.1",
        "pyTelegramBotAPI==2.1.3",
        "requests==2.7.0",
        "tailer==0.4.1",
    ],
    classifiers = [
        "Programming Language :: Python :: 3.4",
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Natural Language :: Portuguese (Brazilian)",
        "Topic :: Communications :: Chat",
    ],
)
