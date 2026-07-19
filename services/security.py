import os
import uuid
import io
import struct
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'heic', 'heif'}

MAGIC_BYTES = {
    b'\xff\xd8\xff': ('jpg', 'jpeg'),
    b'\x89PNG\r\n\x1a\n': ('png',),
    b'GIF87a': ('gif',),
    b'GIF89a': ('gif',),
    b'RIFF': ('webp',),  # WEBP는 "RIFF....WEBP" 형태
    b'\x00\x00\x00\x18ftypheic': ('heic', 'heif'),
    b'\x00\x00\x00\x1cftypheic': ('heic', 'heif'),
    b'\x00\x00\x00\x20ftypheif': ('heic', 'heif'),
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
    ext = (file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else '')
    try:
        if ext in ('heic', 'heif'):
            try:
                import pillow_heif
                pillow_heif.register_heif_opener()
            except Exception:
                pass
        img = Image.open(file)
        # EXIF orientation 자동 적용 (회전 깨짐 방지)
        try:
            exif = img.getexif()
            if exif is not None:
                orientation = exif.get(0x0112)
                if orientation and orientation != 1:
                    rotations = {3: 180, 6: 270, 8: 90}
                    if orientation in rotations:
                        img = img.rotate(rotations[orientation], expand=True)
        except Exception:
            pass
        img = img.convert('RGB')
        out = io.BytesIO()
        fmt = 'JPEG'
        if file.filename.rsplit('.', 1)[1].lower() == 'png':
            fmt = 'PNG'
            img = img.convert('RGBA')
        elif file.filename.rsplit('.', 1)[1].lower() == 'gif':
            fmt = 'GIF'
        save_kwargs = {'optimize': True}
        if fmt == 'JPEG':
            # 회전을 이미 적용했으므로 EXIF orientation 태그를 제거 (다시 돌아가는 것 방지)
            try:
                new_exif = img.getexif()
                if 0x0112 in new_exif:
                    del new_exif[0x0112]
                save_kwargs['exif'] = new_exif
            except Exception:
                pass
        img.save(out, format=fmt, **save_kwargs)
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
    if ext in ('heic', 'heif'):
        ext = 'jpg'
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(save_dir, safe_name)

    try:
        file.seek(0)
        _raw = file.read()
        from PIL import Image as _PI
        try:
            _o = _PI.open(io.BytesIO(_raw))
            _oex = _o.getexif().get(0x0112, 'none')
        except Exception:
            _oex = 'err'
    except Exception:
        _raw = b''
        _oex = 'err'

    sanitized = sanitize_image(file)
    if sanitized:
        with open(save_path, 'wb') as f:
            f.write(sanitized.read())
    else:
        file.seek(0)
        file.save(save_path)

    try:
        from PIL import Image as _PI2
        _r = _PI2.open(save_path)
        _rex = _r.getexif().get(0x0112, 'none')
        _rsize = _r.size
    except Exception as e:
        _rex = f'err:{e}'; _rsize = '?'
    try:
        with open('/tmp/save_dbg.log', 'a') as _lf:
            _lf.write(f"save {safe_name} | incoming_EXIF={_oex} | result_EXIF={_rex} result_size={_rsize}\n")
            _lf.flush()
    except Exception:
        pass

    return f"/static/uploads/{os.path.basename(save_dir)}/{safe_name}"


def apply_watermark(image_path, text, position='bottom-right', opacity=0.5, font_scale=0.04):
    """이미지에 워터마크 텍스트 추가. 처리 후 덮어씀."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.open(image_path).convert('RGBA')
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        font_size = max(12, int(min(img.size) * font_scale))
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", font_size)
            except Exception:
                font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        padding = int(font_size * 0.5)

        positions = {
            'bottom-right': (img.width - tw - padding, img.height - th - padding),
            'bottom-left': (padding, img.height - th - padding),
            'top-right': (img.width - tw - padding, padding),
            'top-left': (padding, padding),
            'center': ((img.width - tw) // 2, (img.height - th) // 2),
        }
        pos = positions.get(position, positions['bottom-right'])

        alpha = int(255 * opacity)
        draw.text(pos, text, font=font, fill=(255, 255, 255, alpha))

        result = Image.alpha_composite(img, overlay).convert('RGB')
        result.save(image_path, format='JPEG', optimize=True)
        return True
    except Exception as e:
        try:
            with open('/tmp/watermark_dbg.log', 'a') as f:
                f.write(f"watermark error: {e}\n")
        except Exception:
            pass
        return False