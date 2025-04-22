import setuptools


def get_requires() -> list[str]:
    with open("requirements.txt", encoding="utf-8") as f:
        file_content = f.read()
        lines = [line.strip() for line in file_content.strip().split("\n") if not line.startswith("#")]
        return lines


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="wangpancli",
    entry_points={"console_scripts": [
            "wangpancli=wangpancli:main",
            "pancli=wangpancli:main",
            "wpcli=wangpancli:main"
        ]
    },
    version="0.1.0",
    author="Tang Yubin",
    author_email="tang-yu-bin@qq.com",
    description="cloud storage CLI (Command Line Interface)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitee.com/aierwiki/wangpancli",
    packages=setuptools.find_packages(),
    python_requires=">=3.10.0",
    install_requires=get_requires(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
