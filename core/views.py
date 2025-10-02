# core/views.py

from rest_framework import viewsets, status, generics, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timezone

# --- Importaciones para drf-spectacular ---
from drf_spectacular.utils import extend_schema

from .models import (
    EmpresaTercera, Trabajador, LineaProducto, Producto, Orden, ItemOrden,
    Etapa, Proceso, Subproceso, SeguimientoProduccion, RegistroAsistencia, RegistroActividad
)
from .serializers import (
    EmpresaTerceraSerializer, TrabajadorSerializer, LineaProductoSerializer, ProductoSerializer,
    OrdenSerializer, ItemOrdenSerializer, EtapaSerializer, SeguimientoProduccionSerializer
)

# --- Serializers inline para documentación ---
class CarritoAddItemSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField(help_text="ID del producto a agregar.")
    cantidad = serializers.IntegerField(default=1, help_text="Cantidad del producto.")

class CarritoUpdateItemSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField(help_text="Nueva cantidad del item. Si es 0, se elimina.")

# --- Vistas para Administración (CRUDs básicos) ---

class EmpresaTerceraViewSet(viewsets.ModelViewSet):
    """API para gestionar Empresas de Terceros."""
    queryset = EmpresaTercera.objects.all()
    serializer_class = EmpresaTerceraSerializer
    permission_classes = [IsAdminUser]

class TrabajadorViewSet(viewsets.ModelViewSet):
    """API para gestionar Trabajadores. Permite buscar por nombre, apellido o código."""
    queryset = Trabajador.objects.all()
    serializer_class = TrabajadorSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['nombres', 'apellidos', 'codigo']
    filterset_fields = ['tipo', 'empresa_tercera']

class LineaProductoViewSet(viewsets.ModelViewSet):
    """API para gestionar las Líneas de Productos."""
    queryset = LineaProducto.objects.all()
    serializer_class = LineaProductoSerializer
    permission_classes = [IsAdminUser]

class ProductoViewSet(viewsets.ModelViewSet):
    """API para Productos. Permite buscar por nombre o código y filtrar por línea."""
    queryset = Producto.objects.all().select_related('linea')
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    search_fields = ['nombre', 'codigo']
    filterset_fields = ['linea']
    ordering_fields = ['nombre', 'codigo']

# --- Vistas para el Flujo de Pedidos y Carrito ---

class CarritoViewSet(viewsets.ViewSet):
    """API para gestionar el carrito de compras."""
    permission_classes = [IsAuthenticated]
    # Se añade serializer_class para ayudar a la generación del schema
    serializer_class = OrdenSerializer

    def get_cart(self, user):
        """Obtiene o crea un carrito para el usuario."""
        cart, created = Orden.objects.get_or_create(usuario=user, estado=Orden.EstadoOrden.CARRITO)
        return cart

    @extend_schema(summary="Ver el carrito actual", responses={200: OrdenSerializer})
    @action(detail=False, methods=['get'], url_path='ver')
    def ver_carrito(self, request):
        """Muestra el contenido del carrito actual."""
        cart = self.get_cart(request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @extend_schema(summary="Agregar un item al carrito", request=CarritoAddItemSerializer, responses={201: OrdenSerializer})
    @action(detail=False, methods=['post'], url_path='agregar')
    def agregar_item(self, request):
        """Añade un producto al carrito o actualiza su cantidad."""
        producto_id = request.data.get('producto_id')
        cantidad = int(request.data.get('cantidad', 1))
        
        if not producto_id or cantidad <= 0:
            return Response({"error": "ID de producto y cantidad válida son requeridos."}, status=status.HTTP_400_BAD_REQUEST)

        cart = self.get_cart(request.user)
        producto = get_object_or_404(Producto, id=producto_id)
        
        item, created = ItemOrden.objects.get_or_create(orden=cart, producto=producto)
        if not created:
            item.cantidad += cantidad
        else:
            item.cantidad = cantidad
        item.save()
        
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Actualizar un item del carrito", request=CarritoUpdateItemSerializer, responses={200: OrdenSerializer})
    @action(detail=True, methods=['patch'], url_path='actualizar')
    def actualizar_item(self, request, pk=None):
        """Modifica la cantidad de un item en el carrito."""
        cantidad = int(request.data.get('cantidad', 0))
        cart = self.get_cart(request.user)
        item = get_object_or_404(ItemOrden, id=pk, orden=cart)
        
        if cantidad > 0:
            item.cantidad = cantidad
            item.save()
        else:
            item.delete()
            
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @extend_schema(summary="Eliminar un item del carrito", responses={204: None})
    @action(detail=True, methods=['delete'], url_path='eliminar')
    def eliminar_item(self, request, pk=None):
        """Elimina un item del carrito."""
        cart = self.get_cart(request.user)
        item = get_object_or_404(ItemOrden, id=pk, orden=cart)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    @extend_schema(summary="Procesar el carrito como un pedido", responses={200: OrdenSerializer})
    @action(detail=False, methods=['post'], url_path='procesar')
    def procesar_pedido(self, request):
        """Convierte el carrito en un pedido procesado y listo para producción."""
        cart = self.get_cart(request.user)
        if not cart.items.exists():
            return Response({"error": "El carrito está vacío."}, status=status.HTTP_400_BAD_REQUEST)
        
        cart.estado = Orden.EstadoOrden.PROCESADA
        cart.lote_asignado = request.data.get('lote', f"LOTE-{cart.codigo_orden}")
        cart.save()
        
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    # Necesario para que self.get_serializer() funcione en un ViewSet básico
    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)


class OrdenViewSet(viewsets.ReadOnlyModelViewSet):
    """API para ver Órdenes procesadas."""
    serializer_class = OrdenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Evita un error al generar el schema si no hay un usuario autenticado
        if getattr(self, 'swagger_fake_view', False):
            return Orden.objects.none()
        
        # Excluye los carritos, solo muestra ordenes reales
        return Orden.objects.filter(usuario=self.request.user).exclude(estado=Orden.EstadoOrden.CARRITO)

# --- Vistas para Flujo de Producción ---

class FlujoProduccionViewSet(viewsets.ReadOnlyModelViewSet):
    """API para ver las Etapas, Procesos y Subprocesos del flujo de producción."""
    queryset = Etapa.objects.all().prefetch_related('procesos__subprocesos')
    serializer_class = EtapaSerializer
    permission_classes = [IsAuthenticated]

class SeguimientoProduccionViewSet(viewsets.ModelViewSet):
    """API para gestionar el seguimiento de la producción de los items de una orden."""
    queryset = SeguimientoProduccion.objects.all()
    serializer_class = SeguimientoProduccionSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(summary="Asignar trabajadores a un subproceso")
    @action(detail=True, methods=['post'], url_path='asignar-trabajadores')
    def asignar_trabajadores(self, request, pk=None):
        """Asigna uno o más trabajadores a un subproceso."""
        seguimiento = self.get_object()
        trabajadores_ids = request.data.get('trabajadores_ids', [])
        
        if not isinstance(trabajadores_ids, list):
            return Response({"error": "Se espera una lista de IDs de trabajadores."}, status=status.HTTP_400_BAD_REQUEST)

        trabajadores = Trabajador.objects.filter(id__in=trabajadores_ids)
        seguimiento.trabajadores_asignados.set(trabajadores)
        
        for trabajador in trabajadores:
            RegistroAsistencia.objects.update_or_create(
                seguimiento=seguimiento, trabajador=trabajador, fecha=datetime.now().date(),
                defaults={'asistio': True}
            )

        return Response(self.get_serializer(seguimiento).data)

    @extend_schema(summary="Controlar el cronómetro de un subproceso")
    @action(detail=True, methods=['post'], url_path='control-tiempo')
    def controlar_tiempo(self, request, pk=None):
        """Controla el cronómetro: INICIO, PAUSA, REANUDAR, FIN."""
        seguimiento = self.get_object()
        evento = request.data.get('evento', '').upper()
        
        if not seguimiento.trabajadores_asignados.exists():
            return Response({"error": "No hay trabajadores asignados a este subproceso."}, status=status.HTTP_400_BAD_REQUEST)

        if evento not in [e.value for e in RegistroActividad.TipoEvento]:
            return Response({"error": f"Evento no válido. Use: {', '.join([e.value for e in RegistroActividad.TipoEvento])}"}, status=status.HTTP_400_BAD_REQUEST)
        
        now = datetime.now(timezone.utc)
        ultima_actividad = seguimiento.actividades.order_by('-timestamp').first()

        if evento == 'INICIO':
            if seguimiento.estado != 'PENDIENTE':
                return Response({"error": "El trabajo ya ha sido iniciado."}, status=status.HTTP_400_BAD_REQUEST)
            seguimiento.estado = 'EN_PROGRESO'
            seguimiento.fecha_inicio = now

        elif evento == 'PAUSA':
            if seguimiento.estado != 'EN_PROGRESO':
                return Response({"error": "El trabajo no está en progreso."}, status=status.HTTP_400_BAD_REQUEST)
            duracion = (now - ultima_actividad.timestamp).total_seconds()
            seguimiento.duracion_total_segundos += int(duracion)
            seguimiento.estado = 'PAUSADO'

        elif evento == 'REANUDAR':
            if seguimiento.estado != 'PAUSADO':
                return Response({"error": "El trabajo no está pausado."}, status=status.HTTP_400_BAD_REQUEST)
            seguimiento.estado = 'EN_PROGRESO'

        elif evento == 'FIN':
            if seguimiento.estado not in ['EN_PROGRESO', 'PAUSADO']:
                return Response({"error": "El trabajo no puede ser finalizado en su estado actual."}, status=status.HTTP_400_BAD_REQUEST)
            if seguimiento.estado == 'EN_PROGRESO':
                duracion = (now - ultima_actividad.timestamp).total_seconds()
                seguimiento.duracion_total_segundos += int(duracion)
            seguimiento.estado = 'FINALIZADO'
            seguimiento.fecha_fin = now
        
        RegistroActividad.objects.create(seguimiento=seguimiento, tipo_evento=evento, usuario=request.user)
        seguimiento.save()
        
        return Response(self.get_serializer(seguimiento).data)