gunicorn final_smartshroom.wsgi:application \
  --timeout 300 \
  --workers 1 \
  --threads 2 \
  --worker-class sync \
  --bind 0.0.0.0:$PORT