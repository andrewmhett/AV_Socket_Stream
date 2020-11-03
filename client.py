import socket
import tkinter
import threading
import atexit
import sys
import pygame

main=tkinter.Tk()
main.title("AV Stream Client")
s = socket.socket()
port=12345

pygame.display.init()

main.protocol('WM_DELETE_WINDOW',lambda: (exit(0),main.destroy()))

atexit.register(s.close)

server_ip=""
video_menu=None

def connect(ip):
    global server_ip
    try:
        s.connect((ip,port))
        server_ip=ip
        ipinf.destroy()
        ipent.destroy()
        ipbut.destroy()
        receiveText.pack()
        sendText.pack()
        b1.pack()
        threading.Thread(target=Receive).start()
    except Exception as e:
        ipinf.configure(text="Failed to connect to server")

data_length=0
main_button_text="Send"
data_id=""
aspect_ratio=[0,0]
width=0
height=0

def read_video_frame_from_buffer(length):
    data=b""
    counter=0
    while counter<(length-length%2048):
        counter+=2048
        data+=s.recv(2048)
    tmp_data=b""
    for i in range(length-sys.getsizeof(data)):
        while tmp_data == b"":
            tmp_data=s.recv(1)
        data+=tmp_data
    return data

def Receive():
    global b1
    global data_length
    global main_button_text
    global video_menu
    global data_id
    global aspect_ratio
    global width
    global height
    while True:
        if data_length>0:
            if data_id != "V_FRAME_DATA" and (data_length < width*height*3 if width>0 else True):
                data=s.recv(data_length-49).decode()
                if data.startswith("ID:"):
                    data_id=data.split("ID:")[1]
                if data.startswith("M:"):
                    serverTextVar.set(data.split("M:")[1])
                if data.startswith("VL:"):
                    video_menu=tkinter.OptionMenu(main, selected_video_name, *(data.split("VL:")[1].split(",")))
                    b1.destroy()
                    sendText.destroy()
                    video_menu.pack()
                    b1=tkinter.Button(main,text=main_button_text,command=send_button_callback)
                    b1.pack()
                if data.startswith("RB:"):
                    main_button_text=data.split("RB:")[1]
                    b1.configure(text=main_button_text)
                if data.startswith("VI:"):
                    width=int(data.split("VI:")[1].split(",")[0])
                    height=int(data.split("VI:")[1].split(",")[1])
                    display=pygame.display.set_mode((int(width),int(height)))
                    pygame.display.flip()
            else:
                data=read_video_frame_from_buffer(data_length)
                display.blit(pygame.image.frombuffer(data,(width,height),"RGB"),(0,0))
                pygame.display.flip()
                data_id=""
            data_length=0
        else:
            data=s.recv(17)
            if data.startswith(b"LENGTH"):
                data=data.decode()
                data_length=int(data.split("LENGTH:")[1])

def format_length(length):
    out_str=""
    for i in range(10-len(str(length))):
        out_str+="0"
    out_str+=str(length)
    return out_str

def send_data(data):
    s.send("LENGTH:{0}".format(format_length(sys.getsizeof(data))).encode("utf-8"))
    s.send(data.encode('utf-8'))

def send_button_callback():
    global video_menu
    global toggle_pause_button
    global rewind_button
    global ff_button
    global media_control_frame
    msg=""
    if main_button_text == "Play":
        msg="VN:"+selected_video_name.get()
    else:
        msg=sendText.get()
    try:
        send_data(msg)
        if main_button_text == "Play":
            b1.destroy()
            video_menu.destroy()
            media_control_frame=tkinter.Frame(main)
            toggle_pause_button=tkinter.Button(media_control_frame,text="\u23EF",command=lambda: send_data("C:TOGGLE_PAUSE"))
            rewind_button=tkinter.Button(media_control_frame,text="\u23EA",command=lambda: send_data("C:REWIND"))
            ff_button=tkinter.Button(media_control_frame,text="\u23E9",command=lambda: send_data("C:FAST_FORWARD"))
            toggle_pause_button.pack(side=tkinter.LEFT)
            rewind_button.pack(side=tkinter.LEFT)
            ff_button.pack(side=tkinter.LEFT)
            media_control_frame.pack()
    except ConnectionResetError:
        while True:
            connect(ip)
            time.sleep(5)

def getip():
    connect(ipent.get())

b1=tkinter.Button(main,text="Send",command=send_button_callback)
sendText=tkinter.Entry(main)
serverTextVar = tkinter.StringVar()
selected_video_name = tkinter.StringVar()
receiveText = tkinter.Label(main,textvariable=serverTextVar)
ipinf=tkinter.Label(main,text="Enter server IP")
ipent=tkinter.Entry(main)
ipbut=tkinter.Button(main,text="Enter",command=getip)
ipinf.pack()
ipent.pack()
ipbut.pack()
main.mainloop()
