import struct

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSlot, QByteArray, QIODevice, Qt, QTimer, QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt5.QtWidgets import *
import crcmod
import pyqtgraph as pg
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
        self.width = 1200
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
        self.flow_button = QPushButton('设置流量')
        self.flow_line_edit = QLineEdit('0')
        # 限制输入为1-9999
        flow_validator = QRegExpValidator()
        flow_validator.setRegExp(QRegExp('[1-9]\\d{0,3}'))

        self.flow_line_edit.setValidator(flow_validator)


        self.init_ui()


        self.create_items()
        self.create_signal_slot()

        self.flow_data = []  # 流量数据
        self.artery_data = [] # 动脉压数据
        self.fresh_data = [] # 新鲜液压力

        self.latest_flow_data = 0  # 最新的流量数据
        self.latest_artery_data = 0  # 最新的动脉压数据
        self.latest_fresh_data = 0 # 最新的新鲜液侧压力数据
        self.serial_data_string = ""  # 所有的数据字符串
        self.serial_data_cursor = 0  # 数据指针
        self.serial_data_list = []  # 数据存储列表


    # 设置实例
    def create_items(self):
        # Qt 串口类
        self.serial = QSerialPort(self)
        self.serial.readyRead.connect(self.receive_data)
        self.get_available_ports()
        # self.timer = QTimer(self)  # 初始化一个定时器
        # self.timer.timeout.connect(self.flow_ui)
        # self.timer.start(50)  # 设置计时间隔 50ms 并启动


    def init_ui(self):
        left_widget = QWidget()
        right_widget = self.create_right_widget()
        serial_widget = self.create_serial_widget()
        control_widget = self.control_widget()

        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        left_layout.addWidget(serial_widget)
        left_layout.addWidget(control_widget)
        left_widget.setLayout(left_layout)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        main_layout.addWidget(splitter)
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        QtCore.QMetaObject.connectSlotsByName(self)

    def create_right_widget(self):
        tab_widget = QTabWidget()
        self.flow_widget = pg.GraphicsLayoutWidget()
        self.vein_artery_widget = pg.GraphicsLayoutWidget()
        self.pressure_widet = pg.GraphicsLayoutWidget()
        self.serial_widget = QWidget()
        tab_widget.addTab(self.serial_widget, '串口显示')
        tab_widget.addTab(self.flow_widget, '流量')
        tab_widget.addTab(self.vein_artery_widget, '脉压')
        tab_widget.addTab(self.pressure_widet, '压力')

        self.flow_plot = self.flow_widget.addPlot()
        self.vein_artery_plot = self.vein_artery_widget.addPlot()
        self.dialysis_plot = self.pressure_widet.addPlot()
        # 设置画笔颜色宽度
        self.green_pen = pg.mkPen((0,220,0), width=1.2,cosmetic=False,style=QtCore.Qt.SolidLine)

        self.flow_plot.showGrid(x=True, y=True, alpha=0.5)  # 把X和Y的表格打开
        self.flow_plot.setLabel('left', text='ml/min')  # 靠左
        self.flow_plot.setLabel('bottom', text='时间', units='s')
        self.flow_plot.setTitle('蠕动泵流量')  # 表格的名字
        self.flow_plot.setRange(xRange=[0,300])
        self.flow_plot.setRange(yRange=[0,500])
        # 动静脉压力的图表
        self.vein_artery_plot.addLegend(size=(100, 50), offset=(0, 0))  # 设置图形的图例
        self.vein_artery_plot.showGrid(x=True, y=True,alpha = 0.5)  # 把X和Y的表格打开
        self.vein_artery_plot.setLabel('left', text='mmHg')  # 靠左
        self.vein_artery_plot.setLabel('bottom', text='时间', units='s')
        self.vein_artery_plot.setTitle('动静脉压力')  # 表格的名字
        self.vein_artery_plot.setRange(yRange=[0,500])
        self.arterial_pressure_curve = self.vein_artery_plot.plot(pen='k', name='动脉压', symbol='o', symbolSize=4, symbolPen=(0, 0, 0),
                                    symbolBrush=(0, 0, 0))
        self.venous_pressure_curve = self.vein_artery_plot.plot(pen='r', name='静脉压', symbol='t', symbolSize=4, symbolPen=(255, 0, 0),
                                    symbolBrush=(255, 0, 0))

         # 透析液压力状况的图表
        self.dialysis_plot.addLegend(size=(100, 50), offset=(0, 0))  # 设置图形的图例
        self.dialysis_plot.showGrid(x=True, y=True)  # 把X和Y的表格打开
        self.dialysis_plot.setLabel('left', text='mmHg')  # 靠左
        self.dialysis_plot.setLabel('bottom', text='时间', units='s')
        self.dialysis_plot.setTitle('透析液压力')  # 表格的名字
        self.dialysis_plot.setRange(yRange=[0, 500])

        self.curve_1 = self.dialysis_plot.plot(pen='b', name='新鲜液', symbol='o', symbolSize=4, symbolPen=(0, 0, 0),
                                    symbolBrush=(0, 0, 0))
        self.curve_2 = self.dialysis_plot.plot(pen='g', name='废弃液', symbol='t', symbolSize=4, symbolPen=(255, 0, 0),
                                    symbolBrush=(255, 0, 0))



        self.serial_ui()
        return tab_widget

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
    # 串口设置区数值
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
        grid.addWidget(self.flow_line_edit,8,0)
        grid.addWidget(self.flow_button,8,1)
        group_box.setLayout(grid)

        return group_box

    # 测量控制
    def control_widget(self):
        group_box = QGroupBox()
        grid = QGridLayout()
        grid.addWidget(QLabel('测量间隔（ms）:'),0,0)
        self.interval_line_edit = QLineEdit()
        grid.addWidget(self.interval_line_edit,0,1)
        self.start_button = QPushButton("开始测量")
        self.clear_button = QPushButton("清除数据")
        grid.addWidget(self.start_button,1,0)
        grid.addWidget(self.clear_button,1,1)
        group_box.setLayout(grid)
        return group_box


    # 设置信号与槽
    def create_signal_slot(self):
        self.refresh_button.clicked.connect(self.get_available_ports)
        self.connect_button.clicked.connect(self.connect_button_clicked)
        self.clear_show_button.clicked.connect(self.receive_browser.clear)
        self.flow_button.clicked.connect(self.set_flow_data)


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
            QMessageBox.critical(self, '错误', '没有选择串口')
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

    def serial_send(self, data):
        # 发送消息按钮
        if not self.serial.isOpen():
            print('串口未连接')
            return
        self.serial.write(data)


    # 串口接收数据
    def receive_data(self):
        if self.serial.bytesAvailable():
            # 当数据可读取时
            # 这里只是简答测试少量数据,如果数据量太多了此处readAll其实并没有读完
            # 需要自行设置粘包协议

            rx_data = self.serial.readAll()
            # if self.hex_show_check.isChecked():
                # 如果勾选了hex显示
            rx_data = rx_data.toHex()
            rx_data = rx_data.data()
            self.serial_data_string = str(rx_data)
            self.analysis()
            for i in self.serial_data_list:
                num = int(i[6:10], 16)
                # 标识流量计数据
                if i.startswith("aa"):
                    if num == 65535:
                        num = -1
                    self.update_flow_data(num)
                    print("流量计数据为:"+str(num))
                elif i.startswith("ab"):
                    if num == 65535:
                        num = -1
                    self.update_artery_data(num)
                    print("动脉压数据为:"+str(num))
                elif i.startswith("ac"):
                    if num == 65535:
                        num = -1
                    self.update_update_vein_data(num)
                    print("静脉压数据为:" + str(num))
                elif i.startswith("ad"):
                    if num == 65535:
                        num = -1
                    self.update_fresh_data(num)
                    print("动脉压数据为:"+str(num))

            self.serial_data_list = []
            # 注意串口指针的位置
            self.serial_data_cursor = 0
            try:
                self.receive_browser.append('收到: ' + rx_data.decode('gb2312'))
                print("收到的数据为:"+rx_data.decode('gb2312'))

            except:
                # 解码失败
                self.receive_browser.append('收到: ' + repr(rx_data))
                print(repr(rx_data))

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

    def analysis(self):
        # 从字符串的第 serial_data_cursor 位开始寻找到末尾
        new_data = self.serial_data_string[self.serial_data_cursor:]
        # print newData
        regex = re.compile(r'\w{2}0302\w{8}')
        result_list = regex.findall(new_data)
        # 如果没找到匹配字符串直接返回
        if len(result_list) == 0:
            print("Find Failed: " + new_data)
            return
        for i in range(len(result_list)):

            if self.data_test(result_list[i]):
                self.serial_data_cursor += len(result_list[i])
                print(result_list[i]+"Right Data")
                self.serial_data_list.append(result_list[i])
            else:
                self.serial_data_cursor += 6  #6=\w{2}+0302
                print(result_list[i] + "Wrong Data")
                self.analysis()

    # 数据校验
    def data_test(self, data):
        # 除去校验位的数据
        data_temp = data[:-4]
        if data[-4:] == self.crc_sum(data_temp):
            return True
        else:
            return False

    def crc_sum(self, data_temp):
        temp = b''
        while data_temp:
            # 将不同的变量打包在一起，成为一个字节字符串
            # bytes
            temp += struct.pack('<H', int(data_temp[:2],16))[0:1]
            data_temp = data_temp[2:]
        # 进行CRC16校验
        crc16 = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
        # 以两位十六进制方式补齐，不显示OX
        crc_l = '{:02x}'.format((crc16(temp) & 0XFF))
        crc_h = '{:02x}'.format((crc16(temp) >> 8))
        # print(crcL)
        # print(crcH)
        return crc_l + crc_h

    # 更新流量数据
    def update_flow_data(self, data):
        self.flow_data.append(data)
        self.flow_plot.setRange(xRange=[self.latest_flow_data-30, self.latest_flow_data])
        self.latest_flow_data += 1
        self.flow_plot.clear()
        self.flow_plot.plot(pen=self.green_pen).setData(self.flow_data[:self.latest_flow_data])

    # 更新动脉压数据
    def update_artery_data(self, data):
        self.artery_data.append(data)
        self.vein_artery_plot.setRange(xRange=[self.latest_artery_data-30, self.latest_artery_data])
        self.latest_artery_data += 1
        self.arterial_pressure_curve.clear()
        self.arterial_pressure_curve.setData(self.artery_data[:self.latest_artery_data])

    # 更新静脉压数据
    def update_vein_data(self, data):
        self.artery_data.append(data)
        self.vein_artery_plot.setRange(xRange=[self.latest_artery_data - 30, self.latest_artery_data])
        self.latest_artery_data += 1
        self.venous_pressure_curve.clear()
        self.venous_pressure_curve.setData(self.artery_data[:self.latest_artery_data])

    # 更新新鲜液压力
    def update_fresh_data(self, data):
        self.fresh_data.append(data)
        self.dialysis_plot.setRange(xRange=[self.latest_fresh_data - 30, self.latest_fresh_data])
        self.latest_fresh_data += 1
        self.dialysis_plot.clear()
        self.dialysis_plot.plot(pen=self.green_pen).setData(self.fresh_data[:self.latest_fresh_data])


    # 设置目标流量
    def set_flow_data(self):
        print(self.flow_line_edit.text())
        text = self.send_edit.toPlainText()
        if not self.flow_line_edit.text():
            QMessageBox.critical(self, '参数错误', '请检验是否输入参数')
            return
        #流量范围为两个字节
        data = '100302'+ '{:04x}'.format(int(self.flow_line_edit.text()))
        data = data + self.crc_sum(data)
        data = bytes.fromhex(data)
        # 发送数据
        # 打印bytes可能会显示ascii对应的字符
        self.serial_send(data)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ui = Hemodialysis()
    ui.show()
    sys.exit(app.exec_())