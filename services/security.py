import os
import uuid
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

# 1. 파일 확장자 검사 (해킹용 악성 스크립트 실행 방지)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 2. [주민 자치 기능] 리 단위 자동 폴더 생성 및 격리 저장 기술
def save_village_file(file, upload_folder, town, village):
    if not file or not allowed_file(file.filename):
        return None

    # 주민의 주소지로 격리된 폴더 생성 (예: static/uploads/강상면_병산리/)
    folder_name = f"{town}_{village}"
    target_dir = os.path.join(upload_folder, folder_name)
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # 중복 및 덮어쓰기 방지를 위한 암호화 고유 파일명 부여 (UUID 적용)
    clean_name = secure_filename(file.filename)
    safe_name = f"{uuid.uuid4().hex}_{clean_name}"
    
    save_path = os.path.join(target_dir, safe_name)
    file.save(save_path)
    
    # 웹 브라우저가 접근할 수 있는 상대 경로 반환
    return f"/static/uploads/{folder_name}/{safe_name}"