loop=true
while $loop
do
    loop=false
    python run.py
    if [ -f .COOLQBOT_RESTART ]
    then
        loop=true
        rm .COOLQBOT_RESTART
    fi
done
