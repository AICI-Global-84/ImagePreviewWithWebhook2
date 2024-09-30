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
from google.oauth2 import service_account
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
        """Authenticate and create a Google Drive API service."""
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        credentials = service_account.Credentials.from_service_account_file(
            'path/to/your/credentials.json', scopes=SCOPES)
        service = build('drive', 'v3', credentials=credentials)
        return service

     @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save and send to webhook."}),
                "filename_prefix": ("STRING", {"default": "ComfyUI", "tooltip": "The prefix for the file to save."}),
                "webhook_url": ("STRING", {"default": "https://your-n8n-webhook-url.com", "tooltip": "The n8n webhook URL to send the image information to."})
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("image_url",)
    FUNCTION = "process_and_send_image"
    OUTPUT_NODE = True
    CATEGORY = "image"

    def upload_to_google_drive(self, image_path):
        """Upload image to Google Drive and return the shared URL."""
        file_metadata = {'name': os.path.basename(image_path), 'parents': ['your_drive_folder_id']}
        media = MediaFileUpload(image_path, mimetype='image/png')
        file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        # Get file ID and create a shareable link
        file_id = file.get('id')
        self.drive_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
        return f"https://drive.google.com/uc?id={file_id}"

    def process_and_send_image(self, images, filename_prefix="ComfyUI", webhook_url="", prompt=None, extra_pnginfo=None):
        # (same as the original code for processing images)

        for batch_number, image in enumerate(images):
            # Save image as before
            full_path = self.save_image(image, batch_number, filename_prefix, counter)

            # Upload image to Google Drive
            public_image_url = self.upload_to_google_drive(full_path)
            if not public_image_url:
                print(f"Failed to upload image for batch {batch_number}. Skipping...")
                continue

            # Send webhook
            if webhook_url:
                self.send_webhook(webhook_url, public_image_url, file, subfolder, prompt, extra_pnginfo)

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
