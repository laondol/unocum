import requests

B = 'http://localhost:5000'
ok = 0
fail = 0

def test(name, status, expected=200):
    global ok, fail
    s = 'O' if status == expected else 'X'
    if s == 'O': ok += 1
    else: fail += 1
    print(f'  [{s}] {name} ({status})')

print('=== 1. 페이지 접근 ===')
s1 = requests.Session()
test('GET /legal/write', s1.get(f'{B}/legal/write').status_code)
test('GET /legal/schedule', s1.get(f'{B}/legal/schedule').status_code)
test('GET /legal/list', s1.get(f'{B}/legal/list').status_code)

print('\n=== 2. 비회원 상담 작성 ===')
r = s1.post(f'{B}/legal/write', data={
    'email':'guest@test.com','title':'비회원 테스트','content':'법률상담 내용입니다','author_name':'게스트','password':'1234'
})
result = 'OK' if r.status_code == 200 else f'FAIL: {r.text[:80]}'
test(f'POST /legal/write (비회원) {result}', r.status_code)

print('\n=== 3. 회원 상담 작성 ===')
s2 = requests.Session()
s2.post(f'{B}/login', data={'username':'user@test.com','password':'pw1234'}, allow_redirects=True)
r2 = s2.post(f'{B}/legal/write', data={
    'email':'user@test.com','title':'회원 테스트','content':'회원의 상담입니다','author_name':'강감찬'
})
result2 = 'OK' if r2.status_code == 200 else f'FAIL: {r2.text[:80]}'
test(f'POST /legal/write (회원) {result2}', r2.status_code)

print('\n=== 4. 게시판 접근 권한 ===')
# 비로그인: 회원글 안보임, 비회원글 보임
r3 = s1.get(f'{B}/legal/list')
has_member = '회원 테스트' in r3.text
has_guest = '비회원 테스트' in r3.text
test(f'비로그인→비회원글 보임', 200 if has_guest else 403)
test(f'비로그인→회원글 숨김', 200 if not has_member else 403)

# 회원 로그인: 자신글+비회원글 보임
r4 = s2.get(f'{B}/legal/list')
has_own = '회원 테스트' in r4.text
has_guest2 = '비회원 테스트' in r4.text
test(f'회원→내글 보임', 200 if has_own else 403)
test(f'회원→비회원글 보임', 200 if has_guest2 else 403)

# 다른 회원 글 확인
s3 = requests.Session()
s3.post(f'{B}/login', data={'username':'admin@unocum.kr','password':'pw1234'}, allow_redirects=True)
r5 = s3.get(f'{B}/legal/list')
has_other = '회원 테스트' in r5.text
test(f'관리자→모든글 보임', 200 if has_other else 403)

print(f'\n=== 결과: OK {ok}, FAIL {fail} ===')
