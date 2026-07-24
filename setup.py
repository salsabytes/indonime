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
  name='videodec',
  ext_modules=ext_modules,
)