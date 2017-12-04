from pip.req import parse_requirements
from setuptools import setup

reqs = [str(ir.req) for ir in
        parse_requirements('requirements.txt', session='')]

tests_require = [
]

setup(
    name='py_proxy',
    version='0.1',
    packages=['transer'],
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
