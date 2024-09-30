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

class ImagePreviewWithWebhook:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4
        self.drive_service = self.authenticate_google_drive()

    def authenticate_google_drive(self):
        """Authenticate and create a Google Drive API service."""
        SCOPES = ['https://www.googleapis.com/auth/drive']
        # Đường dẫn đến file credentials của bạn
        credentials_path = '/content/drive/My Drive/SD-Data/comfyui-n8n-aici01-7679b55c962b.json'  # Thay đổi đường dẫn này cho đúng
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES)  # Sử dụng đường dẫn từ Google Drive
        return build('drive', 'v3', credentials=credentials)



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
        try:
            file_metadata = {'name': os.path.basename(image_path), 'parents': ['your_drive_folder_id']}  # Cập nhật ID thư mục
            media = MediaFileUpload(image_path, mimetype='image/png')
            file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

            # Get file ID and create a shareable link
            file_id = file.get('id')
            self.drive_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
            return f"https://drive.google.com/uc?id={file_id}"
        except Exception as e:
            print(f"An error occurred while uploading to Google Drive: {e}")
            return None


    def save_image(self, image, batch_number, filename_prefix, counter):
        """Save image to the output directory with a specified filename format."""
        i = 255. * image.cpu().numpy()
        img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
    
        full_output_folder, filename, _, _, _ = folder_paths.get_save_image_path(filename_prefix, self.output_dir, img.width, img.height)
        
        filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
        file = f"{filename_with_batch_num}_{counter:05}_.png"
        full_path = os.path.join(full_output_folder, file)
        img.save(full_path)  # Lưu ảnh vào tệp
    
        return full_path

    def process_and_send_image(self, images, filename_prefix="ComfyUI", webhook_url="", prompt=None, extra_pnginfo=None):
        results = []  # Khởi tạo danh sách results
        counter = 0  # Khởi tạo biến counter

        for batch_number, image in enumerate(images):
            # Save image as before (giả định bạn có hàm save_image)
            full_path = self.save_image(image, batch_number, filename_prefix, counter)

            # Upload image to Google Drive
            public_image_url = self.upload_to_google_drive(full_path)
            if not public_image_url:
                print(f"Failed to upload image for batch {batch_number}. Skipping...")
                continue

            # Send webhook (giả định bạn có hàm send_webhook)
            if webhook_url:
                self.send_webhook(webhook_url, public_image_url, filename_prefix, prompt, extra_pnginfo)

            results.append({
                "filename": full_path,  # Sử dụng full_path cho filename
                "subfolder": os.path.dirname(full_path),  # Lấy subfolder từ full_path
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
