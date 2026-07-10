import os
import uuid
import io
import struct
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

MAGIC_BYTES = {
    b'\xff\xd8\xff': ('jpg', 'jpeg'),
    b'\x89PNG\r\n\x1a\n': ('png',),
    b'GIF87a': ('gif',),
    b'GIF89a': ('gif',),
    b'RIFF': ('webp',),  # WEBP는 "RIFF....WEBP" 형태
}

def check_magic_bytes(data):
    for magic, exts in MAGIC_BYTES.items():
        if data[:len(magic)] == magic:
            return exts
    return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

ALLOWED_MIMETYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}

def validate_upload(file, max_mb=20):
    if not file:
        return False, '파일이 없습니다.'

    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return False, f'허용되지 않는 확장자: .{ext}'

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > max_mb * 1024 * 1024:
        return False, f'파일 크기가 {max_mb}MB를 초과합니다.'

    header = file.read(32)
    file.seek(0)

    magic_exts = check_magic_bytes(header)
    if not magic_exts:
        return False, '이미지 파일이 아닙니다 (매직바이트 불일치).'

    if ext not in magic_exts:
        return False, f'확장자(.{ext})와 실제 파일 형식이 일치하지 않습니다.'

    return True, 'OK'

def sanitize_image(file):
    from PIL import Image
    try:
        img = Image.open(file)
        img = img.convert('RGB')
        out = io.BytesIO()
        fmt = 'JPEG'
        if file.filename.rsplit('.', 1)[1].lower() == 'png':
            fmt = 'PNG'
            img = img.convert('RGBA')
        elif file.filename.rsplit('.', 1)[1].lower() == 'gif':
            fmt = 'GIF'
        img.save(out, format=fmt, optimize=True)
        out.seek(0)
        return out
    except Exception:
        return None

def save_village_file(file, upload_folder, town, village):
    if not file or not allowed_file(file.filename):
        return None

    folder_name = f"{town}_{village}"
    target_dir = os.path.join(upload_folder, folder_name)

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    clean_name = secure_filename(file.filename)
    safe_name = f"{uuid.uuid4().hex}_{clean_name}"

    save_path = os.path.join(target_dir, safe_name)

    sanitized = sanitize_image(file)
    if sanitized:
        with open(save_path, 'wb') as f:
            f.write(sanitized.read())
    else:
        file.seek(0)
        file.save(save_path)

    return f"/static/uploads/{folder_name}/{safe_name}"

def secure_save(file, save_dir, max_mb=20):
    ok, msg = validate_upload(file, max_mb)
    if not ok:
        raise ValueError(msg)

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    ext = file.filename.rsplit('.', 1)[1].lower()
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(save_dir, safe_name)

    sanitized = sanitize_image(file)
    if sanitized:
        with open(save_path, 'wb') as f:
            f.write(sanitized.read())
    else:
        file.seek(0)
        file.save(save_path)

    return f"/static/uploads/{os.path.basename(save_dir)}/{safe_name}"