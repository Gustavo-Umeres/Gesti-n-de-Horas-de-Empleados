# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'empresas-terceras', views.EmpresaTerceraViewSet)
router.register(r'trabajadores', views.TrabajadorViewSet)
router.register(r'lineas-producto', views.LineaProductoViewSet)
router.register(r'productos', views.ProductoViewSet)
router.register(r'ordenes', views.OrdenViewSet, basename='orden')
router.register(r'carrito', views.CarritoViewSet, basename='carrito')
router.register(r'flujo-produccion', views.FlujoProduccionViewSet, basename='flujo-produccion')
router.register(r'seguimiento-produccion', views.SeguimientoProduccionViewSet, basename='seguimiento-produccion')

urlpatterns = [
    path('', include(router.urls)),
]