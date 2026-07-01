import requests
s = requests.Session()
s.post('http://localhost:5000/login', data={'username':'user@test.com','password':'pw1234'}, allow_redirects=True)
r = s.get('http://localhost:5000/village')
# Find the error message
if 'AttributeError' in r.text:
    import re
    m = re.search(r'AttributeError: (.*?)\n', r.text)
    print(m.group(0) if m else 'found but could not extract')
elif 'Exception' in r.text:
    print('Exception found')
elif 'SyntaxError' in r.text:
    print('SyntaxError found')
else:
    print('Unknown error, text[:500]:', r.text[:500])
