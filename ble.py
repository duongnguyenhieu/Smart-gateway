import bluepy.btle as btle  # Thư viện bluepy để giao tiếp với thiết bị BLE (Bluetooth Low Energy)
import time  # Thư viện để quản lý thời gian (đợi, sleep, định thời)
import sys  # Thư viện để xử lý thoát chương trình hoặc lỗi hệ thống

# Định nghĩa thông tin thiết bị mục tiêu
TARGET_DEVICE = "c9:a3:d9:cb:02:b3"  # Địa chỉ MAC của thiết bị BLE (node A_Minh)
DEVICE_NAME = "A_Minh"  # Tên thiết bị, dùng để hiển thị trong log
LBS_UUID = "00001523-1212-efde-1523-785feabcd123"  # UUID của dịch vụ LBS (Link Loss Service hoặc dịch vụ tùy chỉnh)

# Lớp MyDelegate kế thừa từ btle.DefaultDelegate để xử lý thông báo (notification) và chỉ báo (indication)
class MyDelegate(btle.DefaultDelegate):
    def __init__(self):
        super().__init__()  # Gọi constructor của lớp cha
        print("Delegate is ready to receive notifications")  # Thông báo khi delegate được khởi tạo
        
    # Hàm xử lý notification từ characteristic (ví dụ: dữ liệu cảm biến)
    def handleNotification(self, handle, data):
        value = int.from_bytes(data, byteorder='little')  # Chuyển dữ liệu byte thành số nguyên (little-endian)
        print(f"?? Sensor data: {value}")  # In giá trị cảm biến nhận được
        
    # Hàm xử lý indication từ characteristic (ví dụ: trạng thái button)
    def handleIndication(self, handle, data):
        value = int.from_bytes(data, byteorder='little')  # Chuyển dữ liệu byte thành số nguyên
        print(f"?? Button: {'PRESSED' if value else 'RELEASED'}")  # In trạng thái button (nhấn/thả)

# Hàm kết nối trực tiếp với thiết bị BLE
def direct_connect():
    print(f"Connecting directly to {DEVICE_NAME} ({TARGET_DEVICE})...")  # Thông báo đang kết nối
    
    try:
        # Thử kết nối với địa chỉ random (thường dùng trong BLE)
        dev = btle.Peripheral(TARGET_DEVICE, btle.ADDR_TYPE_RANDOM)
        print("? Successfully connected (random address)")  # Thông báo kết nối thành công
        return dev  # Trả về đối tượng Peripheral
    except:
        try:
            # Nếu thất bại, thử kết nối với địa chỉ public
            dev = btle.Peripheral(TARGET_DEVICE, btle.ADDR_TYPE_PUBLIC)
            print("? Successfully connected (public address)")
            return dev
        except Exception as e:
            print(f"? Connection error: {e}")  # In lỗi nếu cả hai lần kết nối đều thất bại
            return None  # Trả về None nếu không kết nối được

# Hàm tìm và thiết lập các characteristic của thiết bị
def setup_characteristics(dev):
    button_char = None  # Lưu characteristic của button (indicate)
    led_char = None  # Lưu characteristic của LED (write)
    sensor_char = None  # Lưu characteristic của cảm biến (notify)

    print("\n?? Searching for services and characteristics...")  # Thông báo đang tìm service/characteristic

    # Duyệt qua tất cả service của thiết bị
    for service in dev.getServices():
        print(f"Service: {service.uuid}")  # In UUID của service

        # Duyệt qua tất cả characteristic của service
        for char in service.getCharacteristics():
            props = []  # Danh sách thuộc tính của characteristic
            if char.properties & 0x02:
                props.append("READ")  # Hỗ trợ đọc
            if char.properties & 0x08:
                props.append("WRITE")  # Hỗ trợ ghi
            if char.properties & 0x10:
                props.append("NOTIFY")  # Hỗ trợ thông báo
            if char.properties & 0x20:
                props.append("INDICATE")  # Hỗ trợ chỉ báo

            # In thông tin chi tiết của characteristic
            print(f"  Characteristic: {char.uuid}")
            print(f"    Handle: {char.getHandle()}, Properties: {', '.join(props)}")

            # Phân loại characteristic dựa trên thuộc tính
            if "INDICATE" in props:
                button_char = char
                print("    ? This is the Button characteristic")  # Gán cho button
            elif "WRITE" in props:
                led_char = char
                print("    ? This is the LED characteristic")  # Gán cho LED
            elif "NOTIFY" in props:
                sensor_char = char
                print("    ? This is the Sensor characteristic")  # Gán cho cảm biến

    return button_char, led_char, sensor_char  # Trả về các characteristic đã tìm được

# Hàm chính của chương trình
def main():
    print("=== Connecting to A_Minh ===")  # Thông báo bắt đầu chương trình
    
    # Kết nối đến thiết bị
    dev = direct_connect()
    if not dev:
        print("Unable to connect. Exiting program...")  # Thoát nếu không kết nối được
        sys.exit(1)
    
    # Gán delegate để xử lý notification/indication
    dev.setDelegate(MyDelegate())
    
    try:
        # Tìm và thiết lập các characteristic
        button_char, led_char, sensor_char = setup_characteristics(dev)
        
        # Kích hoạt notification cho cảm biến
        if sensor_char:
            print("\n>> Enabling notifications for sensor...")
            dev.writeCharacteristic(sensor_char.getHandle() + 1, b"\x01\x00")  # Ghi giá trị để bật notification
        
        # Kích hoạt indication cho button
        if button_char:
            print(">> Enabling indications for button...")
            dev.writeCharacteristic(button_char.getHandle() + 1, b"\x02\x00")  # Ghi giá trị để bật indication
        
        print("\n>> Setup complete!")  # Thông báo hoàn tất thiết lập
        print(">> Listening for data from the device...")  # Bắt đầu lắng nghe dữ liệu
        print(">> Controlling LED every 3 seconds")  # Thông báo điều khiển LED
        print(">> Press Ctrl+C to exit")  # Hướng dẫn thoát chương trình
        
        led_state = False  # Trạng thái LED (bật/tắt)
        counter = 0  # Bộ đếm để kiểm soát keep-alive read

        # Vòng lặp chính
        while True:
            if dev.waitForNotifications(1.0):  # Chờ notification trong 1 giây
                continue  # Nếu nhận được notification, tiếp tục vòng lặp

            # Đọc keep-alive mỗi 10 giây
            if counter % 10 == 0:
                try:
                    if sensor_char and (sensor_char.properties & btle.Characteristic.PROP_READ):
                        value = sensor_char.read()  # Đọc giá trị từ characteristic
                        print(f">> Keep-alive read: {value}")  # In giá trị
                except Exception as e:
                    print(f">> Keep-alive failed: {e}")  # In lỗi nếu đọc thất bại

            # Điều khiển LED mỗi 3 giây
            if int(time.time()) % 3 == 0:
                if led_char:
                    led_state = not led_state  # Đổi trạng thái LED
                    value = b'\x01' if led_state else b'\x00'  # Gán giá trị bật/tắt
                    dev.writeCharacteristic(led_char.getHandle(), value)  # Ghi giá trị để điều khiển
                    print(f">> LED: {'ON' if led_state else 'OFF'}")  # In trạng thái LED
                    time.sleep(1)  # Đợi 1 giây để tránh lặp quá nhanh
            
            counter += 1  # Tăng bộ đếm
    
    except KeyboardInterrupt:
        print("\n>> Stopped by user")  # Thoát khi người dùng nhấn Ctrl+C
    
    except btle.BTLEDisconnectError:
        print("\n>> Device disconnected")  # Xử lý khi thiết bị ngắt kết nối
    
    except Exception as e:
        print(f"\n>> Error: {e}")  # Xử lý các lỗi khác
    
    finally:
        try:
            dev.disconnect()  # Ngắt kết nối thiết bị
            print(">> Disconnected successfully")  # Thông báo ngắt kết nối thành công
        except:
            pass  # Bỏ qua lỗi nếu ngắt kết nối thất bại
