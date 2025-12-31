from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, SelectField, FloatField, IntegerField, DateField, BooleanField, ValidationError
from wtforms.validators import DataRequired, Length, NumberRange, Optional, EqualTo, InputRequired
from datetime import datetime
from .constants import TRAMITES_PREDEFINIDOS, CATEGORIAS_GASTOS

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember = BooleanField('Recordar Sesión')
    submit = SubmitField('Entrar')

class PapeleriaForm(FlaskForm):
    nombre = StringField('Nombre de la papelería', validators=[DataRequired(), Length(min=3, max=100)])
    submit = SubmitField('Agregar')

def validate_tramite_manual(form, field):
    """Validador personalizado para el campo de trámite manual."""
    # `field` es el campo `tramite` del formulario.
    if field.data == 'OTRO':
        tramite_manual_field = form.tramite_manual.data.strip() if form.tramite_manual.data else None
        if not tramite_manual_field or not tramite_manual_field.strip():
            raise ValidationError('Si se elige "OTRO", este campo no puede estar vacío.')

class TramiteForm(FlaskForm):
    papeleria_id = SelectField('Papelería', coerce=int, validators=[DataRequired()])
    # Usamos una función lambda para que las choices se actualicen dinámicamente
    tramite = SelectField(
        'Trámite', 
        choices=lambda: TRAMITES_PREDEFINIDOS + ['OTRO'], 
        validators=[DataRequired(), validate_tramite_manual]
    )
    tramite_manual = StringField('Nombre del trámite (si es "OTRO")')
    precio = FloatField('Precio (auto-completado, puedes editarlo)', validators=[Optional(), NumberRange(min=0)])
    costo = FloatField('Costo', validators=[InputRequired(), NumberRange(min=0)], default=0)
    cantidad = IntegerField('Cantidad', default=1, validators=[DataRequired(), NumberRange(min=1)])
    fecha = DateField('Fecha', format='%Y-%m-%d', default=datetime.today)
    submit = SubmitField('Registrar')

class EditarTramiteForm(FlaskForm):
    fecha = DateField('Fecha', format='%Y-%m-%d', validators=[DataRequired()]) # El formato aquí es para el parseo de WTForms
    tramite = SelectField(
        'Trámite', 
        choices=lambda: TRAMITES_PREDEFINIDOS + ['OTRO'], 
        validators=[DataRequired(), validate_tramite_manual]
    )
    tramite_manual = StringField('Nombre del trámite (si es "OTRO")')
    precio = FloatField('Precio', validators=[InputRequired(), NumberRange(min=0)])
    costo = FloatField('Costo', validators=[InputRequired(), NumberRange(min=0)])
    submit = SubmitField('Guardar Cambios')

class ProveedorForm(FlaskForm):
    nombre = StringField('Nombre del Proveedor', validators=[DataRequired(), Length(min=3, max=100)])
    submit = SubmitField('Agregar Proveedor')

class GastoForm(FlaskForm):
    proveedor_id = SelectField('Proveedor', coerce=int, validators=[DataRequired()])
    descripcion = StringField('Descripción (Opcional)', validators=[Length(max=200)])
    categoria = SelectField('Categoría', choices=CATEGORIAS_GASTOS, validators=[DataRequired()])
    monto = FloatField('Monto', validators=[InputRequired(), NumberRange(min=0)])
    fecha = DateField('Fecha del Gasto', format='%Y-%m-%d', default=datetime.today)
    recibo = FileField('Recibo/Factura (Opcional)', validators=[FileAllowed(['jpg', 'png', 'pdf'], '¡Solo imágenes y PDF!')])
    submit = SubmitField('Registrar Gasto')

class EditarGastoForm(GastoForm): # Hereda de GastoForm
    submit = SubmitField('Guardar Cambios')

class EditarProveedorForm(FlaskForm):
    nombre = StringField('Nombre del Proveedor', validators=[DataRequired(), Length(min=3, max=100)])
    submit = SubmitField('Guardar Cambios')

class EditarPapeleriaForm(FlaskForm):
    nombre = StringField('Nuevo Nombre de la Papelería', validators=[DataRequired(), Length(min=3, max=100)])
    submit = SubmitField('Guardar Cambios')

class CambiarPasswordForm(FlaskForm):
    password_actual = PasswordField('Contraseña Actual', validators=[DataRequired()])
    nuevo_password = PasswordField('Nueva Contraseña', validators=[DataRequired(), Length(min=8, message="La contraseña debe tener al menos 8 caracteres."), EqualTo('confirmar_password', message='Las contraseñas deben coincidir.')])
    confirmar_password = PasswordField('Confirmar Nueva Contraseña', validators=[DataRequired()])
    submit = SubmitField('Cambiar Contraseña')

class UserForm(FlaskForm):
    username = StringField('Nombre de Usuario', validators=[DataRequired(), Length(min=3, max=50)])
    role = SelectField('Rol', choices=[('employee', 'Empleado'), ('admin', 'Administrador')], validators=[DataRequired()])
    password = PasswordField('Contraseña', 
                             validators=[Optional(), 
                                         Length(min=8, message="La contraseña debe tener al menos 8 caracteres."),
                                         EqualTo('confirm_password', message='Las contraseñas deben coincidir.')])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[Optional()])
    submit = SubmitField('Guardar Usuario')

class ConfigForm(FlaskForm):
    """Formulario 'marcador' para la página de configuración.
    No necesita campos definidos aquí, solo se usa para el token CSRF."""
    pass

class CrearUsuarioForm(UserForm):
    """
    Hereda de UserForm pero hace que la contraseña sea obligatoria.
    Se usa específicamente para la creación de nuevos usuarios.
    """
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=8), EqualTo('confirm_password', message='Las contraseñas deben coincidir.')])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[DataRequired()])

class AdminResetPasswordForm(FlaskForm):
    """Formulario para que un admin restablezca la contraseña de otro usuario."""
    nuevo_password = PasswordField('Nueva Contraseña', validators=[
        DataRequired(message="La nueva contraseña no puede estar vacía."),
        Length(min=8, message="La contraseña debe tener al menos 8 caracteres."),
        EqualTo('confirmar_password', message='Las contraseñas no coinciden.')
    ])
    confirmar_password = PasswordField('Confirmar Nueva Contraseña', validators=[DataRequired()])
    submit = SubmitField('Establecer Nueva Contraseña')

class DeleteForm(FlaskForm):
    """Formulario genérico para proteger acciones de eliminación con CSRF."""
    submit = SubmitField('Eliminar')

class DismissNotificationForm(FlaskForm):
    """Formulario para proteger la acción de descartar notificaciones con CSRF."""
    pass
