import os
import time

start_cmd = 'cd /root/rieltbot_deploy/ && screen -md python3.9 bot.py'
not_cmd = 'python3.9 /root/rieltbot_deploy/tgbot/handlers/notifymonitor.py'
stop_cmd = 'pkill -f bot.py'
os.system(not_cmd)

while True:
    os.system(start_cmd)
    time.sleep(3756)
    os.system(stop_cmd)