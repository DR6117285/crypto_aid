from setuptools import setup, find_packages

setup(
    name="crypto_aid",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "streamlit",
        "krakenex",
        "pykrakenapi",
        "pandas",
        "plotly",
        "python-dotenv",
        "websockets",
    ],
)
