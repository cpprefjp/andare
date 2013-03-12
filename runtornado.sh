
pkill -f 'runtornado'
sleep 1
nohup python manage.py runtornado &
echo ""
sleep 1
ps aux | grep runtornado | grep -v grep
