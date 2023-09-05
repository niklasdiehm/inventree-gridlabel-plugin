# -*- coding: utf-8 -*-

import setuptools

from inventree_gridlabel.version import GRIDLABEL_PLUGIN_VERSION

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()


setuptools.setup(
    name="inventree-gridlabel-plugin",

    version=GRIDLABEL_PLUGIN_VERSION,

    author="Niklas Diehm",

    author_email="niklas@diehm-straubenhardt.de",

    description="Inventree plugin for printing labels on a grid",

    long_description=long_description,

    long_description_content_type='text/markdown',

    keywords="inventree label printer printing inventory",

    url="https://github.com/niklasdiehm/inventree-gridlabel-plugin",

    download_url = 'https://github.com/niklasdiehm/inventree-gridlabel-plugin/archive/1.0.0.tar.gz',

    license="MIT",

    packages=setuptools.find_packages(),

    install_requires=[],

    setup_requires=[
        "wheel",
        "twine",
    ],

    python_requires=">=3.6",

    entry_points={
        "inventree_plugins": [
            "GridLabelPlugin = inventree_gridlabel.gridlabel_plugin:GridLabelPlugin"
        ]
    },
)
