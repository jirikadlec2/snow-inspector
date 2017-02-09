import os
import sys
from setuptools import setup, find_packages
from tethys_apps.app_installation import custom_develop_command, custom_install_command

### Apps Definition ###
app_package = 'snow_inspector'
release_package = 'tethysapp-' + app_package
app_class = 'snow_inspector.app:SnowInspector'
app_package_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tethysapp', app_package)

### Python Dependencies ###
dependencies = ['pypng','hs-restclient']

setup(
    name=release_package,
    version='0.0.2',
    description='Show graph of snow cover probability from MODIS sensor for selected location',
    long_description='',
    keywords='',
    author='Jiri Kadlec',
    author_email='jirikadlec2@gmail.com',
    url='http://worldwater.byu.edu',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['tethysapp', 'tethysapp.' + app_package],
    include_package_data=True,
    zip_safe=False,
    install_requires=dependencies,
    cmdclass={
        'install': custom_install_command(app_package, app_package_dir, dependencies),
        'develop': custom_develop_command(app_package, app_package_dir, dependencies)
    }
)
