from rest_framework import serializers
from .models import (
    EmpresaTercera, Trabajador, LineaProducto, Producto, Orden, ItemOrden,
    Etapa, Proceso, Subproceso, SeguimientoProduccion, RegistroAsistencia, RegistroActividad
)
from django.contrib.auth.models import User

# --- Serializadores para Usuarios y Autenticación ---
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email')

# --- Serializadores para Trabajadores ---
class EmpresaTerceraSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmpresaTercera
        fields = '__all__'

class TrabajadorSerializer(serializers.ModelSerializer):
    empresa_tercera_nombre = serializers.CharField(source='empresa_tercera.nombre', read_only=True)

    class Meta:
        model = Trabajador
        fields = ('id', 'nombres', 'apellidos', 'codigo', 'tipo', 'empresa_tercera', 'empresa_tercera_nombre')

# --- Serializadores para Productos y Catálogo ---
class LineaProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaProducto
        fields = '__all__'

class ProductoSerializer(serializers.ModelSerializer):
    linea_nombre = serializers.CharField(source='linea.nombre', read_only=True)
    
    class Meta:
        model = Producto
        fields = ('id', 'nombre', 'codigo', 'presentacion', 'linea', 'linea_nombre')

# --- Serializadores para Carrito y Pedidos ---
class ItemOrdenSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer(read_only=True)
    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Producto.objects.all(), source='producto', write_only=True
    )

    class Meta:
        model = ItemOrden
        fields = ('id', 'producto', 'producto_id', 'cantidad')

class OrdenSerializer(serializers.ModelSerializer):
    items = ItemOrdenSerializer(many=True, read_only=True)
    usuario = UserSerializer(read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Orden
        fields = ('id', 'codigo_orden', 'usuario', 'estado', 'fecha_creacion', 'lote_asignado', 'items', 'total_items')
        read_only_fields = ('codigo_orden', 'usuario', 'fecha_creacion')

    def get_total_items(self, obj):
        return obj.items.count()

# --- Serializadores para Flujo de Producción ---
class SubprocesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subproceso
        fields = '__all__'

class ProcesoSerializer(serializers.ModelSerializer):
    subprocesos = SubprocesoSerializer(many=True, read_only=True)
    
    class Meta:
        model = Proceso
        fields = ('id', 'nombre', 'orden_secuencia', 'subprocesos')

class EtapaSerializer(serializers.ModelSerializer):
    procesos = ProcesoSerializer(many=True, read_only=True)

    class Meta:
        model = Etapa
        fields = ('id', 'nombre', 'orden_secuencia', 'procesos')
        
# --- Serializadores para Seguimiento y Tiempo ---
class RegistroAsistenciaSerializer(serializers.ModelSerializer):
    trabajador = TrabajadorSerializer(read_only=True)
    
    class Meta:
        model = RegistroAsistencia
        fields = '__all__'

class RegistroActividadSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroActividad
        fields = '__all__'

class SeguimientoProduccionSerializer(serializers.ModelSerializer):
    item_orden = ItemOrdenSerializer(read_only=True)
    subproceso_actual = SubprocesoSerializer(read_only=True)
    trabajadores_asignados = TrabajadorSerializer(many=True, read_only=True)
    actividades = RegistroActividadSerializer(many=True, read_only=True)

    class Meta:
        model = SeguimientoProduccion
        fields = (
            'id', 'item_orden', 'subproceso_actual', 'estado', 
            'trabajadores_asignados', 'fecha_inicio', 'fecha_fin', 
            'duracion_total_segundos', 'actividades'
        )
