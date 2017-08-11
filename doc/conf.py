import sys
sys.path.insert(0, '.')

extensions = ['sphinx.ext.autodoc', 'sphinxcontrib.httpdomain']
source_suffix = ['.rst', '.md']
source_parsers = {'.md': 'recommonmark.parser.CommonMarkParser'}

project = 'Meetling'
copyright = '2017 Meetling contributors'
version = release = '0.17.2'

html_theme_options = {
    'logo': 'icon.svg',
    'logo_name': True,
    'description': 'Prepare meetings together',
    'github_user': 'noyainrain',
    'github_repo': 'meetling',
    'github_button': True,
    'github_type': 'star'
}
html_favicon = '../meetling/res/static/images/favicon.png'
html_static_path = ['../meetling/res/static/images/icon.svg']
html_sidebars = {'**': ['about.html', 'navigation.html', 'searchbox.html']}
html_show_sourcelink = False

autodoc_member_order = 'bysource'
