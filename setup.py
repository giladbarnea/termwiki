from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()
packages = find_packages(exclude=["tests?", "*.tests*", "*.tests*.*", "tests*.*", 'pypi_publish.py'])
print(f'{packages = }')
setup_args = dict(name='manuals',
                  # https://packaging.python.org/tutorials/packaging-projects/
                  version='0.0.16',
                  description='',
                  long_description=long_description,
                  long_description_content_type="text/markdown",
                  license='MIT',
                  author='Gilad Barnea',
                  author_email='giladbrn@gmail.com',
                  url='https://github.com/giladbarnea/manuals',
                  packages=packages,
                  keywords=[],
                  install_requires=['more-termcolor','click', 'rich','fuzzysearch'],
                  # pip install -e .[dev]
                  extras_require={
                      'dev': ['pytest',
                              'ipdb',
                              'IPython',
                              'jupyter',
                              'semver',
                              'birdseye'
                              ]
                      },
                  # classifiers=[
                  # https://pypi.org/classifiers/
                  # 'Development Status :: 4 - Beta',
                  # 'Environment :: Console',
                  # 'Intended Audience :: Developers',
                  # "License :: OSI Approved :: MIT License",
                  # 'Operating System :: OS Independent',
                  # "Programming Language :: Python :: 3 :: Only",
                  # 'Topic :: Terminals',
                  #  ],
                  python_requires='>=3.8',
                  )
setup(**setup_args)
