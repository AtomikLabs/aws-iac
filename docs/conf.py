# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "AtomikLabs"
copyright = "2023, Brad Edwards"
author = "Brad Edwards"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["recommonmark", "sphinx_markdown_tables"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "logo_only": True,
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": True,
    # Toc options
    "collapse_navigation": False,
    "sticky_navigation": False,
    "navigation_depth": 3,
    "includehidden": True,
    "titles_only": False
}
html_title = "My amazing documentation"
html_logo = "path/to/logo.png"
html_favicon = "path/to/favicon.ico"

source_suffix = [".rst", ".md"]
