from setuptools import setup, find_packages

setup(
    name="ftgso-sim",
    version="1.0.0",
    packages=find_packages(),
    install_requires=["numpy", "matplotlib", "pandas", "seaborn"],
    python_requires=">=3.8",
)