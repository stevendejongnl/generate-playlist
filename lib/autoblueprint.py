# (folder, blueprint, prefix)
INSTALLED_MODULES = [
    ('routes', 'home', '/'),
    # ('api', 'api', '/api'),
]


def register_blueprint(app):
    from importlib import import_module
    for folder, module, prefix in INSTALLED_MODULES:
        m = import_module(folder)
        print(m)
        print(module)
        print(hasattr(m, module))
        if hasattr(m, module):
            bp = getattr(m, module)
            if prefix.strip() == '/':
                # no prefix
                app.register_blueprint(bp)
            else:
                app.register_blueprint(bp, url_prefix=prefix)