"""
SQLAlchemy models for DocuExpress.
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (Column, Integer, String, Float, ForeignKey, DateTime, Boolean,
                        UniqueConstraint, Index, Date, func)
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default='employee')

    papelerias = relationship('Papeleria', back_populates='user', cascade='all, delete-orphan')
    tramites = relationship('Tramite', back_populates='user', cascade='all, delete-orphan')
    proveedores = relationship('Proveedor', back_populates='user', cascade='all, delete-orphan')
    gastos = relationship('Gasto', back_populates='user', cascade='all, delete-orphan')
    tramite_costos = relationship('TramiteCosto', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Papeleria(db.Model):
    __tablename__ = 'papelerias'
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)    
    is_active = Column(Boolean, default=True, nullable=False) # Añadido para soft delete
    user = relationship('User', back_populates='papelerias')
    precios = relationship('PapeleriaPrecio', back_populates='papeleria', cascade='all, delete-orphan')
    tramites = relationship('Tramite', back_populates='papeleria', cascade='all, delete-orphan')

    __table_args__ = (
        UniqueConstraint('nombre', 'user_id', name='uq_papeleria_nombre_user'),
        Index('idx_papelerias_user', 'user_id'),
    )

class PapeleriaPrecio(db.Model):
    __tablename__ = 'papeleria_precios'
    id = Column(Integer, primary_key=True)
    papeleria_id = Column(Integer, ForeignKey('papelerias.id', ondelete='CASCADE'), nullable=False)
    tramite = Column(String, nullable=False)
    precio = Column(Float, nullable=False)

    papeleria = relationship('Papeleria', back_populates='precios')

    __table_args__ = (UniqueConstraint('papeleria_id', 'tramite'), Index('idx_papeleria_precios_user', 'papeleria_id', 'tramite'),)

class Tramite(db.Model):
    __tablename__ = 'tramites'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    papeleria_id = Column(Integer, ForeignKey('papelerias.id', ondelete='CASCADE'), nullable=False)
    tramite = Column(String, nullable=False)
    fecha = Column(Date, nullable=False)
    precio = Column(Float, nullable=False)
    costo = Column(Float, nullable=False, default=0)
    timestamp = Column(DateTime, default=func.now())

    user = relationship('User', back_populates='tramites')
    papeleria = relationship('Papeleria', back_populates='tramites')

    __table_args__ = (
        Index('idx_tramites_user_fecha', 'user_id', 'fecha'),
        Index('idx_tramites_user_papeleria', 'user_id', 'papeleria_id'),
    )

class TramiteCosto(db.Model):
    __tablename__ = 'tramite_costos'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tramite = Column(String, nullable=False)
    costo = Column(Float, nullable=False)

    user = relationship('User', back_populates='tramite_costos')

    __table_args__ = (UniqueConstraint('user_id', 'tramite'), Index('idx_tramite_costos_user', 'user_id'),)

class Proveedor(db.Model):
    __tablename__ = 'proveedores'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    nombre = Column(String, nullable=False)

    user = relationship('User', back_populates='proveedores')
    gastos = relationship('Gasto', back_populates='proveedor', cascade='all, delete-orphan')

    __table_args__ = (UniqueConstraint('user_id', 'nombre'), Index('idx_proveedores_user', 'user_id'),)

class Gasto(db.Model):
    __tablename__ = 'gastos'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    proveedor_id = Column(Integer, ForeignKey('proveedores.id', ondelete='CASCADE'), nullable=False)
    descripcion = Column(String)
    monto = Column(Float, nullable=False)
    fecha = Column(Date, nullable=False)
    categoria = Column(String, nullable=False, default='OTROS')
    receipt_filename = Column(String)

    user = relationship('User', back_populates='gastos')
    proveedor = relationship('Proveedor', back_populates='gastos')

    __table_args__ = (Index('idx_gastos_user_fecha', 'user_id', 'fecha'),)
