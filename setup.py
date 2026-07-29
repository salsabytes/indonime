from setuptools import setup, find_packages

setup(
  name='indonime',
  packages=find_packages(include=['indonime', 'indonime.*']),
  install_requires=[
    'requests',
    'beautifulsoup4',
    'InquirerPy',
    'rich',
  ],
  entry_points={
    'console_scripts': ['indonime=indonime:main'],
  },
  python_requires='>=3.10',
)
