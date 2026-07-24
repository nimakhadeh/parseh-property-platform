"""تنظیمات Gunicorn برای اجرای پروژه در محیط تولید"""
import multiprocessing

# آدرس bind - از سوکت یونیکس استفاده می‌شود (پیشنهاد شده برای Nginx)
bind = "unix:/opt/parseh_project/run/gunicorn.sock"
# در صورت تمایل به bind روی پورت به جای سوکت، خط زیر را از حالت کامنت خارج کنید:
# bind = "127.0.0.1:8000"

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 60
graceful_timeout = 30
keepalive = 5

accesslog = "/opt/parseh_project/logs/gunicorn-access.log"
errorlog = "/opt/parseh_project/logs/gunicorn-error.log"
loglevel = "info"

pidfile = "/opt/parseh_project/run/gunicorn.pid"

max_requests = 1000
max_requests_jitter = 50
