from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timezone

from .models import (
    EmpresaTercera, Trabajador, LineaProducto, Producto, Orden, ItemOrden,
    Etapa, Proceso, Subproceso, SeguimientoProduccion, RegistroAsistencia, RegistroActividad
)
from .serializers import (
    EmpresaTerceraSerializer, TrabajadorSerializer, LineaProductoSerializer, ProductoSerializer,
    OrdenSerializer, ItemOrdenSerializer, EtapaSerializer, SeguimientoProduccionSerializer
)

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

    def get_cart(self, user):
        """Obtiene o crea un carrito para el usuario."""
        cart, created = Orden.objects.get_or_create(usuario=user, estado=Orden.EstadoOrden.CARRITO)
        return cart

    @action(detail=False, methods=['get'], url_path='ver')
    def ver_carrito(self, request):
        """Muestra el contenido del carrito actual."""
        cart = self.get_cart(request.user)
        serializer = OrdenSerializer(cart)
        return Response(serializer.data)

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
        
        serializer = OrdenSerializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='actualizar')
    def actualizar_item(self, request, pk=None):
        """Modifica la cantidad de un item en el carrito."""
        cantidad = int(request.data.get('cantidad', 0))
        cart = self.get_cart(request.user)
        item = get_object_or_404(ItemOrden, id=pk, orden=cart)
        
        if cantidad > 0:
            item.cantidad = cantidad
            item.save()
        else: # Si la cantidad es 0 o menos, se elimina
            item.delete()
            
        serializer = OrdenSerializer(cart)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'], url_path='eliminar')
    def eliminar_item(self, request, pk=None):
        """Elimina un item del carrito."""
        cart = self.get_cart(request.user)
        item = get_object_or_404(ItemOrden, id=pk, orden=cart)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    @action(detail=False, methods=['post'], url_path='procesar')
    def procesar_pedido(self, request):
        """Convierte el carrito en un pedido procesado y listo para producción."""
        cart = self.get_cart(request.user)
        if not cart.items.exists():
            return Response({"error": "El carrito está vacío."}, status=status.HTTP_400_BAD_REQUEST)
        
        cart.estado = Orden.EstadoOrden.PROCESADA
        cart.lote_asignado = request.data.get('lote', f"LOTE-{cart.codigo_orden}")
        cart.save()
        
        # Aquí se podría iniciar el primer subproceso para cada item
        # (Lógica a implementar según reglas de negocio)
        
        serializer = OrdenSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

class OrdenViewSet(viewsets.ReadOnlyModelViewSet):
    """API para ver Órdenes procesadas."""
    serializer_class = OrdenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
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
    
    @action(detail=True, methods=['post'], url_path='asignar-trabajadores')
    def asignar_trabajadores(self, request, pk=None):
        """Asigna uno o más trabajadores a un subproceso."""
        seguimiento = self.get_object()
        trabajadores_ids = request.data.get('trabajadores_ids', [])
        
        if not isinstance(trabajadores_ids, list):
             return Response({"error": "Se espera una lista de IDs de trabajadores."}, status=status.HTTP_400_BAD_REQUEST)

        trabajadores = Trabajador.objects.filter(id__in=trabajadores_ids)
        seguimiento.trabajadores_asignados.set(trabajadores)
        
        # Registrar asistencia
        for trabajador in trabajadores:
            RegistroAsistencia.objects.update_or_create(
                seguimiento=seguimiento, trabajador=trabajador, fecha=datetime.now().date(),
                defaults={'asistio': True}
            )

        return Response(self.get_serializer(seguimiento).data)

    @action(detail=True, methods=['post'], url_path='control-tiempo')
    def controlar_tiempo(self, request, pk=None):
        """Controla el cronómetro: INICIO, PAUSA, REANUDAR, FIN."""
        seguimiento = self.get_object()
        evento = request.data.get('evento', '').upper()
        
        # Validar que los trabajadores estén asignados y presentes
        if not seguimiento.trabajadores_asignados.exists():
            return Response({"error": "No hay trabajadores asignados a este subproceso."}, status=status.HTTP_400_BAD_REQUEST)

        if evento not in [e.value for e in RegistroActividad.TipoEvento]:
            return Response({"error": f"Evento no válido. Use: {', '.join([e.value for e in RegistroActividad.TipoEvento])}"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Lógica de estados y tiempo
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
            # Calcular tiempo transcurrido desde el último INICIO/REANUDAR
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
            # Si estaba en progreso, añadir el último intervalo de tiempo
            if seguimiento.estado == 'EN_PROGRESO':
                duracion = (now - ultima_actividad.timestamp).total_seconds()
                seguimiento.duracion_total_segundos += int(duracion)
            seguimiento.estado = 'FINALIZADO'
            seguimiento.fecha_fin = now
        
        RegistroActividad.objects.create(seguimiento=seguimiento, tipo_evento=evento, usuario=request.user)
        seguimiento.save()
        
        return Response(self.get_serializer(seguimiento).data)
