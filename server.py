import socket
import threading
import os
import datetime
import atexit
import sys
import time
import cv2

s = socket.socket()
port=12345
s.bind(('',port))
s.listen(5)

atexit.register(s.close)

def format_length(length):
    out_str=""
    for i in range(10-len(str(length))):
        out_str+="0"
    out_str+=str(length)
    return out_str

class TargetConnection():
    def __init__(self,connection):
        self.connection=connection
        self.data_length=0
        self.previous_time=None
        self.current_frame=0
        self.framerate=0
        self.metadata={}
        self.cap=None
        threading.Thread(target=self.receive_command).start()
    def stream_video_data(self):
        while True:
            if self.previous_time != None:
                self.current_frame+=round((datetime.datetime.now()-self.previous_time).seconds/self.framerate)
            self.previous_time=datetime.datetime.now()
            self.send_data("ID:V_FRAME_DATA")
            self.send_data(cv2.cvtColor(self.cap.read(self.current_frame)[1], cv2.COLOR_BGR2RGB).tobytes())
            time.sleep(1/self.framerate)
    def receive_command(self):
        while True:
            if self.data_length>0:
                data=self.connection.recv(self.data_length-49).decode()
                if data.startswith("VN:"):
                    video_name=data.split("VN:")[1]
                    for directory in os.walk('videos'):
                        for video in directory[2]:
                            if video.startswith(video_name):
                                self.filename=video
                    self.send_data("M:Loading {0}...".format(video_name))
                    self.cap=cv2.VideoCapture("videos/"+self.filename)
                    while not self.cap.isOpened():
                        pass
                    self.framerate=self.cap.get(5)
                    print("----LOADING VIDEO----")
                    print(self.filename)
                    self.width=int(self.cap.get(3))
                    self.height=int(self.cap.get(4))
                    print(str(int(self.cap.get(3)))+"x"+str(int(self.cap.get(4))))
                    print("FRAMERATE: {0}".format(self.framerate))
                    print("---------------------")
                    self.send_data("VI:{0},{1}".format(self.width,self.height))
                    threading.Thread(target=self.stream_video_data).start()
                if data.startswith("C:"):
                    command=data.split("C:")[1]
                    if command == "TOGGLE_PAUSE":
                        pass
                    if command == "FAST_FORWARD":
                        pass
                    if command == "REWIND":
                        pass
                self.data_length=0
            else:
                data=self.connection.recv(17).decode()
                self.data_length=int(data.split("LENGTH:")[1])
    def send_data(self,data):
        self.connection.send("LENGTH:{0}".format(format_length(sys.getsizeof(data))).encode("utf-8"))
        if type(data) != bytes:
            self.connection.send(data.encode("utf-8"))
        else:
            last_count=0
            size=0
            for i in range(int((self.width*self.height*3)/2048)):
                self.connection.sendall(data[i*2048:(i+1)*2048])
                size+=2048
            self.connection.sendall(data[size:self.width*self.height*3])

def catch_incoming_connections():
    while True:
        connection, addr = s.accept()
        counter=0
        videos=[]
        for directory in os.walk('videos'):
            videos=directory[2]
        counter=0
        for video in videos:
            videos[counter]=".".join(video.split(".")[:-1])
            counter+=1
        target_connection=TargetConnection(connection)
        if len(videos)>0:
            target_connection.send_data("M:Successfully connected to AV server.\nPlease select a video to play.")
            target_connection.send_data("VL:{0}".format(",".join(videos)))
            target_connection.send_data("RB:Play")
        else:
            connection.send("M:Successfully connected to AV server.\nThere are currently no videos on this server. Reload the client in order to refresh.".encode("utf-8"))

threading.Thread(target=catch_incoming_connections).start()
print("AV server running on {0}, port {1}".format(socket.gethostbyname(socket.gethostname()),port))
