from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="restaurant_ordering_helper",
    version="0.1.0",
    author="team-agent",
    author_email="team-agent@example.com",
    description="A restaurant ordering helper agent that provides personalized food recommendations based on health data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/restaurant-ordering-helper",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
    install_requires=[
        "streamlit>=1.32.0",
        "pandas>=2.2.1",
        "selenium>=4.15.2",
        "webdriver-manager>=4.0.2",
        "python-dotenv>=1.0.0",
        "pyautogen[openai]>=0.8.5",
        "openai>=1.12.0",
        "Pillow>=9.5.0",
        "tiktoken>=0.5.2",
        "asyncio>=3.4.3",
        "pytesseract>=0.3.13",
        "beautifulsoup4>=4.12.3"
    ],
    include_package_data=True,
    package_data={
        "": ["*.csv", "*.txt", "*.md"],
    },
) 