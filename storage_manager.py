import os
import logging
import shutil
from firebase_admin import storage, auth
from datetime import datetime

logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self):
        self.summarized_folder = os.path.abspath('summarized_uploads')
        self.ensure_folder_exists()
        try:
            self.bucket = storage.bucket('clipgenie-f57b9.appspot.com')
        except Exception as e:
            logger.warning(f"Firebase Storage bucket initialization skipped (offline/demo mode): {e}")
            self.bucket = None

    def ensure_folder_exists(self):
        """Ensure the summarized uploads folder exists"""
        os.makedirs(self.summarized_folder, exist_ok=True)
        logger.info(f"Ensured summarized uploads folder exists at: {self.summarized_folder}")

    def move_to_summarized(self, source_path, user_id):
        """Move processed video to summarized folder with user-specific subfolder"""
        try:
            # Create user-specific folder
            user_folder = os.path.join(self.summarized_folder, user_id)
            os.makedirs(user_folder, exist_ok=True)

            # Generate timestamp for unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.basename(source_path)
            base_name, extension = os.path.splitext(filename)
            new_filename = f"{base_name}_{timestamp}{extension}"
            
            destination_path = os.path.join(user_folder, new_filename)

            # Move the file
            shutil.move(source_path, destination_path)
            logger.info(f"Moved processed video to: {destination_path}")

            return destination_path

        except Exception as e:
            logger.error(f"Error moving file to summarized folder: {str(e)}")
            raise

    def upload_to_firebase(self, file_path, user_id):
        """Upload file to Firebase Storage under user's folder"""
        try:
            # Generate Firebase Storage path
            filename = os.path.basename(file_path)
            storage_path = f"users/{user_id}/videos/{filename}"

            # Create a blob and upload the file
            blob = self.bucket.blob(storage_path)
            blob.upload_from_filename(file_path)

            # Get the public URL
            url = blob.generate_signed_url(
                expiration=datetime.now().timestamp() + 3600,  # URL expires in 1 hour
                method='GET'
            )

            logger.info(f"Uploaded file to Firebase Storage: {storage_path}")
            return url

        except Exception as e:
            logger.error(f"Error uploading to Firebase Storage: {str(e)}")
            raise

    def process_video_storage(self, video_path, user_id):
        """Complete process of moving and uploading video"""
        try:
            # Move to summarized folder
            summarized_path = self.move_to_summarized(video_path, user_id)
            
            # Upload to Firebase
            firebase_url = self.upload_to_firebase(summarized_path, user_id)
            
            return {
                'local_path': summarized_path,
                'firebase_url': firebase_url
            }

        except Exception as e:
            logger.error(f"Error in video storage processing: {str(e)}")
            raise