import os
import json
import requests
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import numpy as np
import folder_paths
from base64 import b64encode
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class ImagePreviewWithWebhook:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4
        self.drive_service = self.authenticate_google_drive()

    def authenticate_google_drive(self):
        """Tạo dịch vụ Google Drive API sử dụng API Key."""
        API_KEY = 'AIzaSyAhmeHDqy2oHIsYlZxmYB6LbDuN2irIYTs'  # Thay bằng API Key của bạn
        service = build('drive', 'v3', developerKey=API_KEY)
        return service

    def upload_to_google_drive(self, image_path):
        """Upload ảnh lên Google Drive và trả về URL công khai."""
        file_metadata = {'name': os.path.basename(image_path)}
        media = MediaFileUpload(image_path, mimetype='image/png')

        # Upload file lên Google Drive
        file = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = file.get('id')

        # Cấp quyền công khai cho file
        self.drive_service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        # Trả về link công khai
        public_url = f"https://drive.google.com/uc?id={file_id}&export=download"
        return public_url

    def process_and_send_image(self, images, filename_prefix="ComfyUI", webhook_url="", prompt=None, extra_pnginfo=None):
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        
        results = []
        for batch_number, image in enumerate(images):
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            metadata = PngInfo()
            if prompt is not None:
                metadata.add_text("prompt", json.dumps(prompt))
            if extra_pnginfo is not None:
                for x in extra_pnginfo:
                    metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            file = f"{filename_with_batch_num}_{counter:05}_.png"
            full_path = os.path.join(full_output_folder, file)
            img.save(full_path, pnginfo=metadata, compress_level=self.compress_level)

            # Upload ảnh lên Google Drive
            public_image_url = self.upload_to_google_drive(full_path)
            if not public_image_url:
                print(f"Failed to upload image for batch {batch_number}. Skipping...")
                continue

            # Gửi webhook
            if webhook_url:
                try:
                    payload = {
                        "image_url": public_image_url,
                        "filename": file,
                        "subfolder": subfolder,
                        "prompt": prompt,
                        "extra_info": extra_pnginfo
                    }
                    response = requests.post(webhook_url, json=payload)
                    response.raise_for_status()
                except requests.RequestException as e:
                    print(f"Failed to send webhook: {e}")

            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type,
                "image_url": public_image_url
            })
            counter += 1

        return (public_image_url, {"ui": {"images": results}})


# A dictionary that contains all nodes you want to export with their names
NODE_CLASS_MAPPINGS = {
    "ImagePreviewWithWebhook": ImagePreviewWithWebhook
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "ImagePreviewWithWebhook": "Image Preview with Webhook"
}
    
