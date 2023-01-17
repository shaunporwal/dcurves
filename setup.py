from setuptools import setup, find_packages
import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

VERSION = '1.0.0'
DESCRIPTION = 'Python package for Andrew Vickers\' Decision Curve Analysis method to evaluate prediction models and diagnostic tests'

# Setting up
setup(
    name="dcurves",
    version=VERSION,
    author="Shaun Porwal",
    author_email="<shaun.porwal@gmail.com>",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=long_description,
    packages=find_packages(),
    install_requires=['pandas', 'numpy', 'beartype', 'typing',
                      'pkg_resources', 'statsmodels', 'lifelines',
                      'matplotlib', 'random', 'typing'],
    keywords=['python', 'dcurves', 'decision', 'curve', 'analysis', 'MSK', 'Shaun Porwal'],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ],
    include_package_data=True,
    package_data={'': ['data/*.csv']}
)

