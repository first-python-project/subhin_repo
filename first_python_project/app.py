from flask import Flask, render_template, request
import os
from datetime import datetime
import requests
import zipfile
from flask import send_file
import re
import json
from io import BytesIO

app = Flask(__name__) # 초기화

@app.route('/') # 라우터
def list():
    return render_template('upload.html')

@app.route('/check_source_code', methods=["POST"])
def check_source_code():
    files = request.files.getlist("file[]")
    passed_files = []
    check_list = []

    # 확장자 점검 및 내용 검사 준비
    with open("check_list.txt", 'r', encoding='utf-8') as f:
        content = f.read()
        lines = [line for line in content.split('\n') if not line.strip().startswith("#")]
        for line in lines:
            if line:
                check_list.extend(line.split(','))

    # 파일 검사
    for file in files:
        filename = file.filename
        # 확장자 확인
        if not filename.endswith(('.py', '.cpp', '.java', '.js', '.kt')):
            # 내용 점검
            content = file.stream.read().decode('utf-8')  # 파일 내용 읽기
            file.stream.seek(0)  # 스트림 포인터를 처음으로 되돌림
            if not any(re.findall(check, content) for check in check_list):
                passed_files.append(file)

    # 통과한 파일들을 zip 파일로 묶기
    upload_path = "uploads"
    zip_path = os.path.join(upload_path, "compress.zip")
    os.makedirs(upload_path, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        for file in passed_files:
            file_path = os.path.join(upload_path, file.filename)
            file.save(file_path)
            zip_file.write(file_path, file.filename)

    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)