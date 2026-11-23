# Configuration gunicorn - DataEcon.Ci (dimensionnée pour environ 5 000 utilisateurs par jour)
import multiprocessing
import os

bind = "0.0.0.0:10000"
workers = int(os.environ.get("WEB_CONCURRENCY", min(4, max(2, multiprocessing.cpu_count()))))
worker_class = "gthread"
threads = int(os.environ.get("WEB_THREADS", 8))
timeout = 300                  # importations et exports volumineux
graceful_timeout = 60
keepalive = 5
max_requests = 1500            # recyclage periodique des workers (memoire pandas / matplotlib)
max_requests_jitter = 200
worker_tmp_dir = "/dev/shm"
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
forwarded_allow_ips = "*"
