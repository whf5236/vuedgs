from setuptools import setup

setup(
    name="splatviz_network",
    version="0.0.2",
    description="Network connector for splatviz with WebSocket support",
    author="Whf",
    author_email="123",
    license="MIT License",
    packages=["splatviz_network"],
    install_requires=[
        "torch",
        "websockets",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python"
    ],
)
