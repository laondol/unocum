import requests
B = 'http://localhost:5000'

# Check non-member view
s1 = requests.Session()
r1 = s1.get(f'{B}/legal/list')
print('비로그인 게시판 내용:', r1.text[:500])
print('---')
print('Has 비회원:', '비회원' in r1.text)
print('Has 회원:', '회원' in r1.text)

s2 = requests.Session()
s2.post(f'{B}/login', data={'username':'user@test.com','password':'pw1234'}, allow_redirects=True)
r2 = s2.get(f'{B}/legal/list')
print('\n회원 게시판 내용:', r2.text[:500])
print('---')
print('Has 비회원:', '비회원' in r2.text)
print('Has 회원:', '회원' in r2.text)
