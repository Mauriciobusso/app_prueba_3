import reflex as rx


class GoogleOAuthProvider(rx.Component):
    library = "@react-oauth/google"
    tag = "GoogleOAuthProvider"

    client_id: rx.Var[str]


class GoogleLogin(rx.Component):
    library = "@react-oauth/google"
    tag = "GoogleLogin"

    # Definir el callback correctamente
    on_success: rx.EventHandler[lambda credential_response: [credential_response]]
    on_error: rx.EventHandler[lambda: []]

    @classmethod
    def create(cls, on_success=None, on_error=None, **props):
        """Create GoogleLogin component with proper event handlers"""
        return super().create(
            on_success=on_success or (lambda x: None),
            on_error=on_error or (lambda: None),
            **props
        )
