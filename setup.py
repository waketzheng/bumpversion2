import re
from setuptools import setup

description = 'Version-bump your software with a single command!'

long_description = re.sub(
  "`(.*)<#.*>`_",
  r"\1",
  str(open('README.rst', 'rb').read()).replace(description, '')
)

setup(
    name='advbumpversion',
    version='1.0.0',
    url='https://github.com/andrivet/advbumpversion',
    author='Sebastien Andrivet',
    author_email='sebastien@andrivet.com',
    license='MIT',
    description=description,
    long_description=long_description,
    entry_points={
        'console_scripts': [
            'bumpversion = bumpversion:main',
            'bump2version = bumpversion:main',
            'advbumpversion = bumpversion:main',
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: PyPy',
    ], tests_require=['pytest', 'mock']
)
