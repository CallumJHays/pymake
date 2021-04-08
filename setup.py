from setuptools import setup  # type: ignore

setup(
    name='pymake',
    version='0.0.1',

    description='The power of Makefiles with the flexibility of Python',
    classifiers=[
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',
    ],
    # Specify the Python versions you support here. In particular, ensure
    # that you indicate whether you support Python 2, Python 3 or both.
    # 'Programming Language :: Python :: 3 :: Only'],

    # project_urls={
    #     #'Documentation': 'https://petercorke.github.io/bdsim',
    #     'Source': 'https://github.com/petercorke/bdsim',
    #     'Tracker': 'https://github.com/petercorke/bdsim/issues',
    #     #'Coverage': 'https://codecov.io/gh/petercorke/spatialmath-python',
    # },
    # url='https://github.com/petercorke/bdsim',
    author='Callum Hays',
    author_email='callumjhays@gmail.com',
    keywords='Makefile build-system docker task-runner',
    license='MIT',
    python_requires='>=3.6',
    packages=['pymake'],
    install_requires=['click'],
    entry_points='''
        [console_scripts]
        pymake=pymake.cli:cli
    ''',
)
