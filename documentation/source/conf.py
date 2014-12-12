import sys
import os

project = 'blockip'
copyright = '2014, Zalando SE'
version = '1.0.0'
release = '1.0.0'

master_doc = 'index'
source_suffix = '.rst'
html_static_path = ['.static']
templates_path = ['.templates']

extensions = ['sphinxcontrib.httpdomain']
html_theme = 'nature'
pygments_style = 'sphinx'
