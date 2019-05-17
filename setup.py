from setuptools import setup

setup(
    name='pianoplayer',
    version='2.0.7', #change also in __init__.py and README.md
    packages=['pianoplayer'],
    scripts=['bin/pianoplayer'],
    install_requires=['music21','vtkplotter'], # vtk and numpy are needed but better install them manually
    description='Automatic piano fingering generator. Finds and shows in 3D the best fingering combination to play a score.',
    long_description="""Automatic piano fingering generator. 
    Finds and shows in a 3D visualization the best fingering combination to play a score.

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
# cd ~/Projects/pianoplayer/
# pip install .

# # check version number here and in __init__

# ana3
# git status
# python setup.py sdist bdist_wheel

# git commit -a -m 'comment'
# git push
# twine upload dist/pianoplayer-?.?.?.tar.gz -r pypi

# # check status at  https://pypi.org/project/pianoplayer/
# # check status at  https://github.com/marcomusy/pianoplayer
