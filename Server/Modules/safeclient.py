﻿from Server.Modules.message_dealer import MessageDealer
from Server.Modules.Flogger import Flogger
from threading import Thread
import queue
import socket
import json
import time


class SocketClient:
    """
    使用TCP连接的socket函数封装
    """

    def __init__(self, ip: str, port: int, heart_beat: int = -1, debug=False,
                 warning=False, msg_len: int = 1024, password: str = None,
                 models=Flogger.DLOGG, logpath=None, level=Flogger.L_INFO):
        """
        ip:服务端ip地址
        port:服务端端口
        heart_beat:心跳检测 默认0
        debug: debug选项
        warning: warning选项
        msg_len: 报文长度 默认1024 实测在每秒60帧，4Mbps情况下，报文长度最高3000，否则丢包
        password：AES加密秘钥，默认None
        初始化
        初始化后已经和服务端建立了socket连接
        """
        self.logger = Flogger(models, logpath, level, folder_name="safeclient")
        self.__socket = socket.socket()
        """客户端"""
        self.__port = port
        """服务器端口"""
        self.__host = ip
        """服务器ip"""
        self.debug = debug
        """debug选项"""
        self.warnig = warning
        """是否开启warning"""
        self.heart_beat = heart_beat
        """心跳检测"""
        self.que = queue.Queue()
        """消息队列"""
        self.msg_len = msg_len
        """消息长"""
        self.password = None
        """加密选项,如需加密请直接输入秘钥"""
        if password:
            self.password = password.encode()
        if (password is not None) and (len(password) != 16):
            self.logger.error("秘钥长度非16" + password)
            raise Exception("秘钥长度非16" + password)
        try:
            self.__socket.connect((self.__host, self.__port))
            self.__socket.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, True)
        except Exception as err:
            self.logger.error(str(err) + "无法连接到服务器")
            raise Exception(str(err) + "无法连接到服务器")
        # 以下是初始化logging
        self.logger.info("heart time：" + str(self.heart_beat))
        self.logger.info("ip:" + str(self.__host) + " port:" + str(self.__port))
        self.logger.info("message length:" + str(self.msg_len))
        self.logger.info("debug:" + str(self.debug))

        self.message_thread = Thread(target=self.message_handler)
        self.message_thread.setDaemon(True)
        self.message_thread.setName("client_message_thread")
        self.message_thread.start()
        if heart_beat > 0:
            self.heart_thread = Thread(target=self.beating)
            self.heart_thread.setDaemon(True)
            self.heart_thread.setName("heart_beat_thread")
            self.heart_thread.start()

    def message_handler(self):
        try:
            while True:
                recv_segment = self.__socket.recv(self.msg_len)
                tmpmsg = MessageDealer.decode(recv_segment, self.password)
                for item in tmpmsg:
                    message = None
                    try:
                        self.logger.debug("接收到服务端消息" + str(item))
                        message = json.loads(item)
                        if message["opt"] != 0:
                            self.que.put(message)
                    except Exception as err:
                        self.logger.warning("消息{}不是json格式报文,未解析".format(message) + str(err))
                        self.que.put(item)
        except Exception as err:
            self.logger.error("client closed" + str(err))

    def beating(self):
        while True:
            send_msg = {"opt": 0, "heartbeat": self.heart_beat}
            self.send(send_msg)
            time.sleep(max(0.5, self.heart_beat / 4))

    def send(self, message):
        """
        data:数据 支持str/json格式
        发送数据
        """
        if type(message) == str or message["opt"] != 0:
            self.logger.debug("sending message" + str(message))

        if type(message) == dict:
            message = json.dumps(message)
        message = MessageDealer.encode(message, self.password)
        try:
            self.__socket.sendall(message)
        except Exception as err:
            self.logger.error(str(err))

    def receive(self):
        """
        返回数据(阻塞方式）
        """
        res = self.que.get()
        return res

    def get_message(self):
        """
        获取消息（非阻塞）
        若无消息返回None
        """
        if self.que.empty():
            return None
        res = self.que.get()
        return res

    def get_message_list(self):
        """
        获取消息队列
        """
        res = []
        while not self.que.empty():
            res.append(self.que.get())
        return res

    def close(self):
        """
        关闭连接
        """
        self.logger.info("closed")
        self.__socket.close()


if __name__ == "__main__":
    ip = "localhost"
    port = 25555
    online = False
    if online:
        ip = "124.70.162.60"
    client = SocketClient(ip, port, heart_beat=10, debug=False, msg_len=8192, password="0123456789abcdef")
    cnt = 0
    a = input()
    while True:
        # a = "a" * a
        if a == "0":
            break
        msg = {
            "opt": -1,
            "info": a
        }
        client.send(msg)
        client.send(msg)
        client.send(msg)
        recv = client.get_message()
        while recv is None:
            recv = client.get_message()
        print(recv)
    client.close()
