from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in chemtekscientific/__init__.py
from chemtekscientific import __version__ as version

setup(
	name="chemtekscientific",
	version=version,
	description="hr",
	author="frappe",
	author_email="chemtek@frappe.cloud",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
