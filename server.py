import socket
import threading
import os
import datetime
import atexit
import sys
import time
import cv2

command_s = socket.socket()
video_s = socket.socket()
command_port=12345
video_port=12346
audio_port=12347
command_s.bind(('',command_port))
video_s.bind(('',video_port))
command_s.listen(5)
video_s.listen(5)

atexit.register(command_s.close)
atexit.register(video_s.close)

def format_length(length):
    out_str=""
    for i in range(10-len(str(length))):
        out_str+="0"
    out_str+=str(length)
    return out_str

class TargetConnection():
    def __init__(self,command_c,video_c):
        self.command_c=command_c
        self.video_c=video_c
        self.command_data_length=0
        self.video_data_length=0
        self.previous_time=None
        self.current_frame=0
        self.framerate=0
        self.metadata={}
        self.cap=None
        self.stream_thread=None
        self.streaming=False
        threading.Thread(target=self.receive_command).start()
    def stream_video_data(self):
        while self.streaming:
            if self.previous_time != None:
                self.current_frame+=round((datetime.datetime.now()-self.previous_time).seconds/self.framerate)
            self.previous_time=datetime.datetime.now()
            try:
                self.send_data(self.video_c,cv2.cvtColor(self.cap.read(self.current_frame)[1], cv2.COLOR_BGR2RGB).tobytes())
            except cv2.error:
                self.send_data(self.command_c,"VE")
                self.streaming=False
            time.sleep(1/self.framerate)
    def receive_command(self):
        while True:
            if self.command_data_length>0:
                data=self.command_c.recv(self.command_data_length-49).decode()
                if data == "VQ":
                    self.streaming=False
                    self.send_data(self.command_c,"M:Successfully connected to AV server.\nPlease select a video to play.")
                if data.startswith("VN:"):
                    video_name=data.split("VN:")[1]
                    for directory in os.walk('videos'):
                        for video in directory[2]:
                            if video.startswith(video_name):
                                self.filename=video
                    self.send_data(self.command_c,"M:Loading {0}...".format(video_name))
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
                    self.send_data(self.command_c,"VI:{0},{1}".format(self.width,self.height))
                    self.stream_thread=threading.Thread(target=self.stream_video_data)
                    self.streaming=True
                    self.stream_thread.start()
                if data.startswith("C:"):
                    command=data.split("C:")[1]
                    if command == "TOGGLE_PAUSE":
                        pass
                    if command == "FAST_FORWARD":
                        pass
                    if command == "REWIND":
                        pass
                self.command_data_length=0
            else:
                data=self.command_c.recv(17)
                data=data.decode()
                self.command_data_length=int(data.split("LENGTH:")[1])
    def send_data(self,connection,data):
        connection.send("LENGTH:{0}".format(format_length(sys.getsizeof(data))).encode("utf-8"))
        if connection == self.command_c:
            connection.send(data.encode("utf-8"))
        elif connection == self.video_c:
            last_count=0
            size=0
            for i in range(int((self.width*self.height*3)/2048)):
                connection.sendall(data[i*2048:(i+1)*2048])
                size+=2048
            connection.sendall(data[size:self.width*self.height*3])

def catch_incoming_connections():
    while True:
        command_c, addr = command_s.accept()
        video_c, addr = video_s.accept()
        counter=0
        videos=[]
        for directory in os.walk('videos'):
            videos=directory[2]
        counter=0
        for video in videos:
            videos[counter]=".".join(video.split(".")[:-1])
            counter+=1
        target_connection=TargetConnection(command_c,video_c)
        if len(videos)>0:
            target_connection.send_data(command_c,"M:Successfully connected to AV server.\nPlease select a video to play.")
            target_connection.send_data(command_c,"VL:{0}".format(",".join(videos)))
            target_connection.send_data(command_c,"RB:Play")
        else:
            connection.send("M:Successfully connected to AV server.\nThere are currently no videos on this server. Reload the client in order to refresh.".encode("utf-8"))

threading.Thread(target=catch_incoming_connections).start()
print("AV server running on {0}".format(socket.gethostbyname(socket.gethostname())))
