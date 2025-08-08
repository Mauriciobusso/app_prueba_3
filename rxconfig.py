import reflex as rx

class Config(rx.Config):
    pass

config = Config(
    app_name="app_prueba_3",
    disable_plugins=['reflex.plugins.sitemap.SitemapPlugin'],
)