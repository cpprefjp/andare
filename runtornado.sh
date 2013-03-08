
pkill -f 'runtornado'
sleep 1
nohup python manage.py runtornado &
echo ""
ps aux | grep runtornado | grep -v grep
