ip addr
pwd
hostname -I
ping kafka1
getent hosts kafka1
nc -vz kafka1 9092
curl kafdrop1:9000
exit
clear
getent hosts kafka1
getent hosts kafka2
getent hosts kafka3
python -c "import socket; print(socket.gethostbyname('kafka1'))"
exit
cd /home/jovyan/python-files-jupyter/
ls
python run_generators.py 
pip install kafka-python
exit
which pip
pip install msgpack
exit
python -c "import msgpack; print(msgpack.__version__)"
exit
