"""
Módulo de Backup Automático para DocuExpress
Gestiona backups programados de la base de datos SQLite
"""

import os
import sqlite3
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class BackupManager:
    """Gestor de backups automáticos de base de datos."""
    
    def __init__(self, app=None):
        self.app = app
        self.scheduler = None
        self.backup_dir = None
        self.db_path = None
        self.retention_days = 30
        self.enabled = False
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa el gestor de backups con la configuración de Flask."""
        self.app = app
        self.enabled = os.environ.get('BACKUP_ENABLED', 'True').lower() == 'true'
        
        if not self.enabled:
            logger.info("📦 Backups automáticos deshabilitados")
            return
        
        # Configuración
        base_dir = Path(app.config.get('BASE_DIR', Path(__file__).resolve().parent))
        self.backup_dir = base_dir / os.environ.get('BACKUP_DIR', 'backups')
        self.db_path = Path(app.config.get('DATABASE_PATH'))
        self.retention_days = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))
        
        # Crear directorio de backups
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Iniciar scheduler
        self._start_scheduler()
        
        logger.info(f"📦 Backups automáticos habilitados")
        logger.info(f"   Directorio: {self.backup_dir}")
        logger.info(f"   Retención: {self.retention_days} días")
    
    def _start_scheduler(self):
        """Inicia el scheduler de backups."""
        if self.scheduler is not None:
            return
        
        self.scheduler = BackgroundScheduler(daemon=True)
        
        # Configurar frecuencia de backup
        schedule = os.environ.get('BACKUP_SCHEDULE', 'daily').lower()
        
        if schedule == 'hourly':
            trigger = CronTrigger(minute=0)  # Cada hora en punto
            logger.info("⏰ Backups programados: cada hora")
        elif schedule == 'weekly':
            trigger = CronTrigger(day_of_week='sun', hour=2, minute=0)  # Domingos a las 2 AM
            logger.info("⏰ Backups programados: semanalmente (domingos 2 AM)")
        else:  # daily (por defecto)
            trigger = CronTrigger(hour=2, minute=0)  # Diario a las 2 AM
            logger.info("⏰ Backups programados: diariamente (2 AM)")
        
        self.scheduler.add_job(
            func=self.create_backup,
            trigger=trigger,
            id='database_backup',
            name='Backup automático de base de datos',
            replace_existing=True
        )
        
        # Backup al iniciar (opcional)
        if os.environ.get('BACKUP_ON_START', 'True').lower() == 'true':
            self.scheduler.add_job(
                func=self.create_backup,
                trigger='date',
                run_date=datetime.now() + timedelta(seconds=10),
                id='startup_backup',
                name='Backup inicial al arrancar'
            )
        
        self.scheduler.start()
        logger.info("✅ Scheduler de backups iniciado")
    
    def create_backup(self, manual=False):
        """Crea un backup de la base de datos."""
        if not self.enabled and not manual:
            logger.warning("⚠️ Backups deshabilitados, usa manual=True para forzar")
            return None
        
        try:
            # Validar que existe la base de datos
            if not self.db_path.exists():
                logger.error(f"❌ Base de datos no encontrada: {self.db_path}")
                return None
            
            # Generar nombre del backup con timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"control_papelerias_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # Realizar backup seguro usando SQLite API (evita corrupción si la DB está en uso)
            src = sqlite3.connect(self.db_path)
            dst = sqlite3.connect(backup_path)
            with dst:
                src.backup(dst)
            dst.close()
            src.close()
            
            # Verificar integridad del backup
            if backup_path.exists() and backup_path.stat().st_size > 0:
                logger.info(f"✅ Backup creado exitosamente: {backup_filename}")
                logger.info(f"   Tamaño: {backup_path.stat().st_size / 1024:.2f} KB")
                
                # Limpiar backups antiguos
                self.cleanup_old_backups()
                
                return backup_path
            else:
                logger.error(f"❌ Backup falló: archivo inválido")
                if backup_path.exists():
                    backup_path.unlink()
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creando backup: {e}")
            return None
    
    def cleanup_old_backups(self):
        """Elimina backups más antiguos que el período de retención."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            deleted_count = 0
            
            for backup_file in self.backup_dir.glob('control_papelerias_backup_*.db'):
                # Obtener fecha del nombre del archivo
                try:
                    # Formato: control_papelerias_backup_YYYYMMDD_HHMMSS.db
                    date_str = backup_file.stem.split('_')[-2]
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    if file_date < cutoff_date:
                        backup_file.unlink()
                        deleted_count += 1
                        logger.debug(f"🗑️ Backup antiguo eliminado: {backup_file.name}")
                except (ValueError, IndexError) as e:
                    logger.warning(f"⚠️ No se pudo parsear fecha del backup: {backup_file.name}")
                    continue
            
            if deleted_count > 0:
                logger.info(f"🗑️ {deleted_count} backup(s) antiguo(s) eliminado(s)")
                
        except Exception as e:
            logger.error(f"❌ Error limpiando backups antiguos: {e}")
    
    def list_backups(self):
        """Lista todos los backups disponibles."""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob('control_papelerias_backup_*.db'), reverse=True):
            try:
                stat = backup_file.stat()
                date_str = backup_file.stem.split('_')[-2]
                time_str = backup_file.stem.split('_')[-1]
                file_date = datetime.strptime(f"{date_str}_{time_str}", '%Y%m%d_%H%M%S')
                
                backups.append({
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'date': file_date,
                    'size': stat.st_size,
                    'size_mb': stat.st_size / (1024 * 1024)
                })
            except Exception as e:
                logger.warning(f"⚠️ Error procesando backup {backup_file.name}: {e}")
                continue
        
        return backups
    
    def restore_backup(self, backup_filename):
        """Restaura la base de datos desde un backup."""
        try:
            backup_path = self.backup_dir / backup_filename
            
            if not backup_path.exists():
                logger.error(f"❌ Backup no encontrado: {backup_filename}")
                return False
            
            # Crear backup de seguridad antes de restaurar
            safety_backup = self.db_path.parent / f"{self.db_path.stem}_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(self.db_path, safety_backup)
            logger.info(f"🔒 Backup de seguridad creado: {safety_backup.name}")
            
            # Restaurar
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"✅ Base de datos restaurada desde: {backup_filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error restaurando backup: {e}")
            return False
    
    def shutdown(self):
        """Detiene el scheduler de backups."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("🛑 Scheduler de backups detenido")


# Instancia global
backup_manager = BackupManager()
