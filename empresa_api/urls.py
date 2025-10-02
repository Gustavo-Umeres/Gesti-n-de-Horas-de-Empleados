from django.contrib import admin
from django.urls import path, include

# --- Importaciones para las vistas de Simple JWT ---
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- Rutas de la API de la aplicación 'core' ---
    # Esto conecta con el archivo urls.py que está dentro de tu app 'core'
    path('api/v1/', include('core.urls')),

    # --- Rutas de Autenticación con JWT ---
    # El cliente enviará 'username' y 'password' a esta ruta para obtener los tokens.
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),

    # El cliente puede enviar el 'refresh_token' a esta ruta para obtener un nuevo 'access_token'.
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

