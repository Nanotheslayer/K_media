"""
Регистрация маршрутов
"""
def register_routes(app):
    from webapp_server.routes.main_routes import main_bp
    from webapp_server.routes.chat_routes import chat_bp
    from webapp_server.routes.admin_routes import admin_bp
    from webapp_server.routes.api_routes import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app
