from setuptools import setup, find_packages

setup(
    name="cerebrum",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "pytest",
        "pytest-asyncio",
    ],
    python_requires=">=3.8",
) 