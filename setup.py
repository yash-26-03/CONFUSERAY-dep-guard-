from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dep-guard",
    version="0.6.0",
    description="Static scanner for dependency-confusion attacks in CI/CD pipelines",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={"CONFUSERAY": ["dashboard/*.html", "dashboard/sample_reports/*.json"]},
    python_requires=">=3.8",
    install_requires=["requests>=2.28.0", "pymongo>=4.0"],
    entry_points={
        "console_scripts": [
            "depguard=CONFUSERAY.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Topic :: Security",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
    ],
)
