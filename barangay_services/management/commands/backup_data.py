import os
import shutil
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Backs up the database and media files'

    def handle(self, *args, **options):
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Backup Database (SQLite for now)
        db_path = settings.DATABASES['default']['NAME']
        db_backup_name = f'db_backup_{timestamp}.sqlite3'
        db_backup_path = os.path.join(backup_dir, db_backup_name)
        
        try:
            shutil.copy2(db_path, db_backup_path)
            self.stdout.write(self.style.SUCCESS(f'Database backed up to {db_backup_path}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Database backup failed: {e}'))

        # 2. Backup Media Files
        media_root = settings.MEDIA_ROOT
        if os.path.exists(media_root):
            media_backup_name = f'media_backup_{timestamp}'
            media_backup_path = os.path.join(backup_dir, media_backup_name)
            try:
                shutil.make_archive(media_backup_path, 'zip', media_root)
                self.stdout.write(self.style.SUCCESS(f'Media files backed up to {media_backup_path}.zip'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Media backup failed: {e}'))
        
        # 3. Clean up old backups (keep last 5)
        all_backups = sorted(
            [os.path.join(backup_dir, f) for f in os.listdir(backup_dir)],
            key=os.path.getmtime,
            reverse=True
        )
        if len(all_backups) > 10: # Keep 5 DB + 5 Media archives
            for old_backup in all_backups[10:]:
                os.remove(old_backup)
                self.stdout.write(f'Removed old backup: {old_backup}')
