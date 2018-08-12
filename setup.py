from setuptools import setup

setup(
    name='pianoplayer',
    version='1.0.0', #change also in plotter.py
    packages=['pianoplayer'],
    scripts=['bin/pianoplayer'],
    install_requires=[], # vtk and numpy are needed but better install it manually
    description='Automatic piano fingering generator. Finds and shows the best fingering combination to use to play a score.',
    long_description="""Automatic piano fingering generator.
    Check out https://github.com/marcomusy/pianoplayer for documentation.""",
    author='Marco Musy',
    author_email='marco.musy@gmail.com',
    license='MIT',
    url='https://github.com/marcomusy/pianoplayer',
    keywords='piano fingering',
    classifiers=['Intended Audience :: Science/Research',
                'Intended Audience :: Education',
                'Programming Language :: Python',
                'License :: OSI Approved :: MIT License',
                'Topic :: Scientific/Engineering :: Visualization',
                'Topic :: Scientific/Engineering :: Information Analysis'],
    include_package_data=True
)

##############################################################
# # check examples
# cd ~/Projects/pianoplayer/
# pip install .
# cd examples
# source run_all.sh

# # check version number here and in plotter.py

# ana3
# git status
# python -m pip install --user --upgrade twine
# python setup.py sdist bdist_wheel

# git commit -a -m 'comment'
# git push
# twine upload dist/pianoplayer-?.?.?.tar.gz -r pypi

# # check status at  https://pypi.org/project/pianoplayer/
# # check status at  https://github.com/marcomusy/pianoplayer