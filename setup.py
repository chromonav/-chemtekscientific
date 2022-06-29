from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in chemtech_custom_app/__init__.py
from chemtech_custom_app import __version__ as version

setup(
	name="chemtech_custom_app",
	version=version,
	description="ChemTech",
	author="abc",
	author_email="admin@example.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
