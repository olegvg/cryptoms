from pip.req import parse_requirements
from setuptools import setup, find_packages

reqs = [str(ir.req) for ir in
        parse_requirements('requirements.txt', session='')]

tests_require = [
]

setup(
    name='transer_btc',
    version='0.1',
    packages=find_packages(),
    test_suite='transer.testsuite.__init__',
    install_requires=reqs,
    entry_points={
        'console_scripts': [
            'transer=transer.daemon:main'
        ]
    },
    setup_requires=[
        'flake8',
        'wheel',
        'pytest-runner'
    ],
    zip_safe=True,
    tests_require=tests_require,
    python_requires='>=3.6'
)
