from flask import Flask, render_template, request
import os
import zipfile
from flask import send_file
import re
from flask import Flask, send_file
import openpyxl
import re
from faker import Faker
from docx import Document

app = Flask(__name__) # 초기화

def make_customer_list():
    workbook = openpyxl.Workbook()
    worksheet = workbook.active

    worksheet['A1'] = "이름"
    worksheet['B1'] = "전화번호"
    worksheet['C1'] = "우편번호"
    worksheet['D1'] = "주소"
    worksheet['E1'] = "이메일"

    fake = Faker('ko_KR')


    for row in range(2, 50): #2행부터 시작해 50줄까지 생성
        worksheet.cell(row=row, column=1, value=fake.name())
        worksheet.cell(row=row, column=2, value=fake.phone_number())
        worksheet.cell(row=row, column=3, value=fake.postcode())
        worksheet.cell(row=row, column=4, value=fake.address())
        worksheet.cell(row=row, column=5, value=fake.email())

    workbook.save("customer_list.xlsx")
    return 0


####마스킹 처리####
def make_masking_file(file):
    workbook = openpyxl.load_workbook(file)
    
    #파일 내 중요 정보(전화번호 가운데 3, 4자리, 주소에서 도,시,구로 끝나는 것 제외, 이메일) 정규표현식
    phone_number_pattern = r"\d{2,3}-\d{3,4}-\d{4}"      #전화번호 가운데 4자리 찾기
    email_pattern = "[\w\.-]+@[\w\.-]+"                 #이메일 찾기

    # 모든 시트 순회
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]

        # 각 셀 순회하며 중요정보 찾기
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value:
                    # 셀의 값에서 중요정보 각 패턴 찾기
                    phone_number_in_cell = re.findall(phone_number_pattern, str(cell.value))
                    email_in_cell = re.findall(email_pattern, str(cell.value))

                    if cell.column == 1:  # 이름이 있는 열
                        name = cell.value
                        if len(name) > 1:  # 이름의 길이가 2자 이상인 경우 (성이 포함된 경우)
                            masked_name = name[0] + '*' * (len(name) - 1)  # 성을 제외한 나머지 부분을 마스킹 처리
                            cell.value = masked_name

                    if phone_number_in_cell:
                        # 전화번호 가운데 자릿수가 3자리, 4자리인 경우도 마스킹 처리
                        for phone_number in phone_number_in_cell:
                            split_phone_number = phone_number.split('-')
                            if len(split_phone_number[1]) == 3:
                                #전화번호 가운데 3자리 마스킹 처리
                                masked_phone_number = phone_number[:3] + "-***-" + phone_number[-4:]
                            else:
                                #전화번호 가운데 4자리 마스킹 처리
                                masked_phone_number = phone_number[:4] + "-****-" + phone_number[-4:]
                        cell.value = cell.value.replace(phone_number, masked_phone_number)
                    if email_in_cell:
                        for email in email_in_cell:
                            # 이메일을 마스킹 처리
                            masked_email = email[:4] + "*****" + email[email.index("@"):]
                            cell.value = cell.value.replace(email, masked_email)

    # 수정된 내용을 새로운 파일로 저장
    upload_path = "uploads"
    masked_file = os.path.join(upload_path, "masked_your_excel_file.xlsx")
    workbook.save(masked_file)
    
    # 클라이언트에게 다운로드할 파일을 응답으로 전달
    return masked_file

# 한글 파일인 경우 특정 단어가 있으면 마스킹하는 함수
# txt파일을 통해 특정단어 설정
def process_document(file):
    dir_path = 'static'
    masking_word_txt = 'word.txt'
    mst_path = os.path.join(dir_path, masking_word_txt)
    # txt파일에 저장된 특정 단어 읽기
    def read_masking_word(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            # 공백제거
            return [line.strip() for line in lines]
        
    masking_word = read_masking_word(mst_path)

    # 경로의 doc, docx 파일 찾기 
    upload_path = "uploads"
       
    input_doc = os.path.join(upload_path, file.filename)
    output_doc = os.path.join(upload_path, f"{os.path.splitext(file)[0]}_masking.docx")

    doc = Document(input_doc)

    # doc, docx 파일 특정 단어 변경
    for file_doc in doc.paragraphs:
        for word in masking_word:
            if word in file_doc.text:
                # 단어길이만큼 *로 변경
                masking = '*' * len(word)
                file_doc.text = file_doc.text.replace(word, masking)
                        
    doc.save(output_doc)
    return output_doc

####소스코드 검사####
def make_check_list():
    check_list = []

    with open("check_list.txt", 'r', encoding='utf-8') as f:
        content = f.read()
        lines = [line for line in content.split('\n') if not line.strip().startswith("#")]
        for line in lines:
            if line:
                check_list.extend(line.split(','))
    return check_list


def check_source_code(file):
    check_list = make_check_list()

    # 파일 검사
    filename = file.filename
    # 확장자 확인
    if not filename.endswith(('.py', '.cpp', '.java', '.js', '.kt')):
        # 내용 점검
        content = file.stream.read().decode('utf-8')  # 파일 내용 읽기
        file.stream.seek(0)  # 스트림 포인터를 처음으로 되돌림
        if not any(re.findall(check, content) for check in check_list):
            return True
        
    return False

def make_zip_file(passed_files):
    # 통과한 파일들을 zip 파일로 묶기
    upload_path = "uploads"
    zip_path = os.path.join(upload_path, "compress.zip")
    #os.makedirs(upload_path, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        for file in passed_files:
            if isinstance(file, str):  # 파일 경로인 경우
                zip_file.write(file, os.path.basename(file))
            else:  # 파일 객체인 경우
                file_path = os.path.join(upload_path, file.filename)
                file.save(file_path)
                zip_file.write(file_path, file.filename)

    compressed_file = "compress.zip"
    return compressed_file

@app.route('/') # 라우터
def list():
    #make_customer_list()
    return render_template('upload.html')

@app.route('/check_file', methods=["POST"])
def check_file():
    passed_files = []
    files = request.files.getlist("file[]")

    for file in files:
        filename = file.filename
        if filename.endswith('.xlsx'):
            passed_files.append(make_masking_file(file))
        elif filename.endswith(('.docx', 'doc')):
            passed_files.append(process_document(file))
        elif check_source_code(file):
            passed_files.append(file)

    compressed_file = make_zip_file(passed_files)
    compressed_file_path = os.path.join("uploads", compressed_file)
    return send_file(compressed_file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)