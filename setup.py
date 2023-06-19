from setuptools import setup

setup(
    name="pianoplayer",
    version="2.2.1",  # change also in __init__.py
    packages=["pianoplayer"],
    scripts=["bin/pianoplayer"],
    install_requires=["music21", "vedo"],
    description="Automatic piano fingering generator. Finds and shows in 3D the best fingering combination to play a score.",
    long_description="""Automatic piano fingering generator.
    Finds and shows in a 3D visualization the best fingering combination to play a score.

    Check out https://github.com/marcomusy/pianoplayer for documentation.""",
    author="Marco Musy",
    author_email="marco.musy@gmail.com",
    license="MIT",
    url="https://github.com/marcomusy/pianoplayer",
    keywords="piano fingering",
    classifiers=[
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: Visualization",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    include_package_data=True,
)

##############################################################
# check version number here and in __init__
# git status
# python setup.py sdist bdist_wheel
# git commit -a -m 'comment'
# git push
# twine upload dist/pianoplayer-?.?.?.tar.gz -r pypi
