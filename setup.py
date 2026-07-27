from setuptools import setup

setup(
  name='indonime',
  packages=['indonime', 'ext', 'plugins'],
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
