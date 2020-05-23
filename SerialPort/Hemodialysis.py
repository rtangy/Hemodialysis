import array
import binascii

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSlot, QByteArray, QIODevice, Qt, QTimer
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt5.QtWidgets import *
import pyqtgraph as pg
import numpy as np
import re
import sys

baud_rates = ['1200', '2400', '4800', '9600', '14400', '19200', '38400', '57600', '115200']
verify_bit = ['No', 'Even', 'Odd', 'Space', 'Mark', 'Unknown']
data_bit = ['5', '6', '7', '8']
stop_bite = ['OneStop', 'OneAndHalfStop', 'UnknownStopBits']


class Hemodialysis(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('血透仪')
        self.width = 700
        self.height = int(0.618 * self.width)
        self.resize(self.width, self.height)
        self.refresh_button = QPushButton('刷新')
        self.serial_combobox = QComboBox()
        self.baud_label = QLabel('波特率')
        self.baud_combobox = QComboBox()
        self.baud_combobox.addItems(baud_rates)
        self.baud_combobox.setCurrentIndex(8)   # 设置波特率默认选中值
        self.verify_bit_combobox = QComboBox()  # 校验位下拉列表
        self.verify_bit_combobox.addItems(verify_bit)
        self.verify_bit_combobox.setCurrentIndex(0) # 设置校验位默认选中值
        self.data_bit_combobox = QComboBox()    # 数据位下拉列表
        self.data_bit_combobox.addItems(data_bit)
        self.data_bit_combobox.setCurrentIndex(3)  # 设置数据位默认选中值
        self.stop_bit_combobox = QComboBox()    # 停止位下拉列表
        self.stop_bit_combobox.addItems(stop_bite)
        self.stop_bit_combobox.setCurrentIndex(0)  # 设置停止位默认选中值
        self.connect_button = QPushButton('打开串口')
        self.status_label = QLabel()
        self.flow_button = QPushButton("流量数据")


        self.init_ui()


        self.create_items()
        self.create_signal_slot()

        self.flow_data = [] # 流量数据
        self.lastest_flow_data = 0 # 最新的流量数据
        self.stop_update_flow_data = 1 # 更新流量数据暂停标志

    # 设置实例
    def create_items(self):
        # Qt 串口类
        self.serial = QSerialPort(self)
        self.serial.readyRead.connect(self.receive_data)
        self.get_available_ports()
        self.timer = QTimer(self)  # 初始化一个定时器
        self.timer.timeout.connect(self.flow_ui)
        self.timer.start(50)  # 设置计时间隔 50ms 并启动


    def init_ui(self):
        right_widget = self.create_right_widget()
        serial_widget = self.create_serial_widget()

        main_layout = QHBoxLayout()
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(serial_widget)
        splitter.addWidget(right_widget)
        main_layout.addWidget(splitter)
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        QtCore.QMetaObject.connectSlotsByName(self)

    def create_right_widget(self):
        tab_widget = QTabWidget()
        self.flow_widget = pg.GraphicsLayoutWidget()
        self.serial_widget = QWidget()
        temperature_widget = QWidget()
        tab_widget.addTab(self.serial_widget, '串口显示')
        tab_widget.addTab(self.flow_widget, '流量')
        self.idx = 0
        self.data = array.array('d')  # 可动态改变数组的大小,double型数组
        self.historyLength = 100  # 横坐标长度
        p = self.flow_widget.addPlot()
        p.showGrid(x=True, y=True)  # 把X和Y的表格打开
        p.setRange(xRange=[0, self.historyLength], yRange=[-1.2, 1.2], padding=0)
        p.setLabel(axis='left', text='y / V')  # 靠左
        p.setLabel(axis='bottom', text='x / point')
        p.setTitle('y = sin(x)')  # 表格的名字
        self.curve = p.plot()  # 绘制一个图形
        tab_widget.addTab(temperature_widget, '温度')
        self.serial_ui()
        return tab_widget

    def flow_ui(self):
        self.idx
        tmp = np.sin(np.pi / 50 * self.idx)
        if len(self.data) < self.historyLength * 5:
            self.data.append(tmp)
        else:
            self.data[:-1] = self.data[1:]  # 前移
            self.data[-1] = tmp
        self.curve.setData(self.data)
        self.idx += 1
    def serial_ui(self):
        serial_box = QVBoxLayout()
        receive_box = QHBoxLayout()
        self.hex_show_check = QCheckBox('16进制显示')
        self.clear_show_button = QPushButton('清除')
        receive_box.addStretch(0)
        receive_box.addWidget(QLabel('接收区'))
        receive_box.addStretch(1)
        receive_box.addWidget(self.hex_show_check)
        receive_box.addStretch(3)
        receive_box.addWidget(self.clear_show_button)

        send_box = QHBoxLayout()
        self.hex_send_check = QCheckBox('16进制发送')
        self.send_button = QPushButton('发送')
        self.send_button.setObjectName("send_button")
        send_box.addStretch(0)
        send_box.addWidget(QLabel('发送区'))
        send_box.addStretch(1)
        send_box.addWidget(self.hex_send_check)
        send_box.addStretch(3)
        send_box.addWidget(self.send_button)
        self.receive_browser = QTextBrowser()
        self.send_edit = QTextEdit()
        serial_box.addLayout(receive_box)
        serial_box.addWidget(self.receive_browser)
        serial_box.addLayout(send_box)
        serial_box.addWidget(self.send_edit)

        self.serial_widget.setLayout(serial_box)

    def create_serial_widget(self):
        group_box = QGroupBox('串口设置')
        grid = QGridLayout()

        grid.addWidget(self.refresh_button, 0, 0, 1, 2)
        grid.addWidget(QLabel('串口选择'), 1, 0)
        grid.addWidget(self.serial_combobox, 1, 1)
        grid.addWidget(QLabel('波特率'), 2, 0)
        grid.addWidget(self.baud_combobox, 2, 1)
        grid.addWidget(QLabel('校验位'), 3, 0)
        grid.addWidget(self.verify_bit_combobox, 3, 1)
        grid.addWidget(QLabel('数据位'), 4, 0)
        grid.addWidget(self.data_bit_combobox, 4, 1)
        grid.addWidget(QLabel('停止位'), 5, 0)
        grid.addWidget(self.stop_bit_combobox, 5, 1)

        grid.addWidget(QLabel('串口操作'), 6, 0)
        grid.addWidget(self.connect_button, 6, 1)
        grid.addWidget(self.status_label, 7, 0)
        grid.addWidget(self.flow_button,8,0)
        group_box.setLayout(grid)

        return group_box

    # 设置信号与槽
    def create_signal_slot(self):
        self.refresh_button.clicked.connect(self.get_available_ports)
        self.connect_button.clicked.connect(self.connect_button_clicked)
        self.clear_show_button.clicked.connect(self.receive_browser.clear)
        self.flow_button.clicked.connect(self.request_flow_data)

        # 返回当前系统可用的串口
        com_list = QSerialPortInfo.availablePorts()
        for info in com_list:
            self.serial.setPort(info)
            if self.serial.open(QSerialPort.ReadWrite):
                self.serial_combobox.addItem(info.portName())
                self.serial.close()

    # 打开串口按钮按下
    def connect_button_clicked(self):
        # 打开或关闭串口按钮
        if self.serial.isOpen():
            # 如果串口是打开状态则关闭
            self.serial.close()
            self.refresh_button.setEnabled(True)
            self.serial_combobox.setEnabled(True)
            self.baud_combobox.setEnabled(True)
            self.verify_bit_combobox.setEnabled(True)
            self.data_bit_combobox.setEnabled(True)
            self.stop_bit_combobox.setEnabled(True)
            self.receive_browser.append('串口已关闭')
            self.connect_button.setText('打开串口')
            self.status_label.setText("<font color='grey'>已关闭</font>")

            return

        serial_name = self.serial_combobox.currentText()
        if not serial_name:
            QMessageBox.critical(self,'错误','没有选择串口')
            return
        port = self.ports[serial_name]
        # 根据名字设置窗口
        self.serial.setPortName(port.systemLocation())
        # 设置波特率
        self.serial.setBaudRate(
            getattr(QSerialPort, 'Baud' + self.baud_combobox.currentText()))
        # 设置校验位
        self.serial.setParity(
            getattr(QSerialPort, self.verify_bit_combobox.currentText() + 'Parity'))
        # 设置数据位
        self.serial.setDataBits(
            getattr(QSerialPort, 'Data' + self.data_bit_combobox.currentText()))
        # 设置停止位
        self.serial.setStopBits(  #
            getattr(QSerialPort, self.stop_bit_combobox.currentText()))

        # NoFlowControl          没有流程控制
        # HardwareControl        硬件流程控制(RTS/CTS)
        # SoftwareControl        软件流程控制(XON/XOFF)
        # UnknownFlowControl     未知控制
        self.serial.setFlowControl(QSerialPort.NoFlowControl)
        # 读写方式打开串口
        ok = self.serial.open(QIODevice.ReadWrite)
        if ok:
            self.receive_browser.append('打开串口成功')
            self.connect_button.setText('关闭串口')
            self.refresh_button.setEnabled(False)
            self.serial_combobox.setEnabled(False)
            self.baud_combobox.setEnabled(False)
            self.verify_bit_combobox.setEnabled(False)
            self.data_bit_combobox.setEnabled(False)
            self.stop_bit_combobox.setEnabled(False)
            self.status_label.setText("<font color='green'>已关闭</font>")
        else:
            self.receive_browser.append('打开串口失败')

    @pyqtSlot()
    def on_send_button_clicked(self):
        # 发送消息按钮
        if not self.serial.isOpen():
            print('串口未连接')
            return
        text = self.send_edit.toPlainText()
        if not text:
            return
        text = QByteArray(text.encode('gb2312'))
        if self.hex_send_check.isChecked():
            # 如果勾选了hex发送
            text = text.toHex()
        # 发送数据
        print('发送数据', text)
        self.serial.write(text)


    # 串口接收数据
    def receive_data(self):
        if self.serial.bytesAvailable():
            # 当数据可读取时
            # 这里只是简答测试少量数据,如果数据量太多了此处readAll其实并没有读完
            # 需要自行设置粘包协议

            rx_data = self.serial.readAll()
            if self.hex_show_check.isChecked():
                # 如果勾选了hex显示
                rx_data = rx_data.toHex()
            rx_data = rx_data.data()
            try:
                self.receive_browser.append('收到: ' + rx_data.decode('gb2312'))
            except:
                # 解码失败
                self.receive_browser.append('收到: ' + repr(rx_data))

    def get_available_ports(self):
        self.serial_combobox.clear()
        # 获取可用的串口
        self.ports = {}  # 用于保存串口的信息
        infos = QSerialPortInfo.availablePorts()
        infos.reverse()  # 逆序
        for info in infos:
            # 通过串口名字-->关联串口变量
            self.ports[info.portName()] = info
            self.serial_combobox.addItem(info.portName())
    def request_flow_data(self):
        '''发送流量请求数据'''

    def rece_serial_data(self,data):
        print(data)





if __name__ == '__main__':
    app = QApplication(sys.argv)
    ui = Hemodialysis()
    ui.show()
    sys.exit(app.exec_())
