import setuptools

from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setuptools.setup(
    name="mkdocs-render-openapi-schemaobj",
    version="0.0.1",
    author="Shashidhar",
    python_requires='>=3.6',
    author_email="bangu97@gmail.com",
    description="MKDocs plugin for rendering openapi schema objects.",
    url="https://github.com/shashi-banger/mkdocs-render-openapi-schemaobj",
    py_modules=["render_openapi_schemaobj"],
    install_requires=["mkdocs", "Jinja2"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'mkdocs.plugins': [
            'render_openapi_schemaobj = render_openapi_schemaobj:SchemaRenderPlugin',
        ]
    },
    long_description=long_description,
    long_description_content_type='text/markdown'
)