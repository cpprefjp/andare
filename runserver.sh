
pkill -f 'runserver'
sleep 1
nohup python manage.py runserver 8080 &
echo ""
sleep 1
ps aux | grep runserver | grep -v grep
