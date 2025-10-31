import os
import shutil
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import ExtractedImage

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
        Command to delete old user image folders and DB records.
        When an image is older than 2 days, it will be removed. Also the folder containing the image will be deleted.
        This is a handy function to call from the server in a cronjob.

        0 2 * * * python3 manage.py cleanup_old_images >> /var/log/django_cleanup.log 2>&1
    """
    help = 'Delete all user image folders (and DB records) older than 2 days.'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=2)
        old_images = ExtractedImage.objects.filter(created_at__lt=cutoff)
        count = old_images.count()

        if not count:
            logger.info("No old images found to delete.")
            return

        logger.info(f"Found {count} old images. Starting cleanup...")

        # Gather all folders that contain expired images
        folders_to_delete = set()
        for img in old_images:
            folder_path = os.path.dirname(img.image.path)
            folders_to_delete.add(folder_path)

        # Delete DB records first to keep consistency
        old_images.delete()

        # Now delete the folders
        for folder in folders_to_delete:
            try:
                if os.path.isdir(folder):
                    shutil.rmtree(folder)
                    logger.info(f"Deleted folder: {folder}")
            except Exception as e:
                logger.error(f"Failed to delete folder {folder}: {e}")

        logger.info("✅ Cleanup complete.")
