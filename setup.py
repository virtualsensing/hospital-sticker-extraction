from setuptools import setup, find_packages

setup(
    name="hospital-sticker-extraction",
    version="0.1.0",
    description="Extract patient data from South African hospital admission stickers using AI vision",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "anthropic>=0.40.0",
        "Pillow>=10.0.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "sticker-extract=extractor.cli:main",
        ],
    },
)
