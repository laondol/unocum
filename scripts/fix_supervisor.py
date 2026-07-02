conf = """[program:yp_dev]
command=/home/ubuntu/yp_project/venv/bin/gunicorn -w 1 -b 127.0.0.1:5001 --timeout 120 run:app
directory=/home/ubuntu/yp_project_dev
user=ubuntu
autostart=true
autorestart=true
environment=DB_NAME=yangpyeong_v10_dev.db
stdout_logfile=/home/ubuntu/yp_project/logs/gunicorn_dev_stdout.log
stderr_logfile=/home/ubuntu/yp_project/logs/gunicorn_dev_stderr.log
"""
with open('/etc/supervisor/conf.d/yp_dev.conf', 'w') as f:
    f.write(conf)
print('Config written')
