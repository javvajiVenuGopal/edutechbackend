import os

def save_file(file, folder):
    os.makedirs(f"app/uploads/{folder}", exist_ok=True)

    file_path = f"app/uploads/{folder}/{file.filename}"

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    return file_path