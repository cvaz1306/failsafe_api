from setuptools import setup, find_packages

setup(
    name='failsafeapi',
    version='0.1.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['websockets>=10.0', 'python-gnupg'],
    url='https://github.com/cvaz1306/failsafeapi',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Security',
        'Topic :: System :: Networking',
        'Development Status :: 3 - Alpha',
    ],
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Christopher Vaz',
    author_email='christophervaz160@gmail.com',
    description='Secure failsafe websocket API with PGP authentication',
    license='MIT',
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'failsafeapi = failsafeapi.__main__:main'
        ]
    }
)
