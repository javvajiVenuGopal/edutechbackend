import os
import shutil
from fastapi import UploadFile
from uuid import uuid4


BASE_DIR = "uploads"


def save_file(file: UploadFile, folder: str):

    folder_path = os.path.join(BASE_DIR, folder)

    os.makedirs(folder_path, exist_ok=True)

    filename = f"{uuid4()}_{file.filename}"

    file_path = os.path.join(folder_path, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return file_path