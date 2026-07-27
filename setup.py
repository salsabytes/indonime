from setuptools import setup, Extension
import pybind11

ext_modules = [
  Extension(
    'videodec',
    ['src/decoder.cpp'],
    include_dirs=[pybind11.get_include()],
    language='c++',
    extra_compile_args=['-O3'],
  ),
]

setup(
  name='indonime',
  packages=['indonime', 'ext', 'plugins'],
  ext_modules=ext_modules,
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