import sys
sys.path.insert(0, '.')

extensions = ['sphinx.ext.autodoc', 'sphinxcontrib.httpdomain']

project = 'Meetling'
copyright = '2015 Meetling contributors'
version = release = '0.13.2'

html_logo = '../meetling/res/static/images/icon.svg'
html_favicon = '../meetling/res/static/images/favicon.png'
html_sidebars = {'**': ['globaltoc.html', 'relations.html', 'searchbox.html']}

autodoc_member_order = 'bysource'
