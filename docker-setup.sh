#!/bin/sh
# Kịch bản của @VanillaNahida
# Tệp này được sử dụng để tự động tải xuống các tệp cần thiết cho dự án này chỉ bằng một cú nhấp chuột và tự động tạo một thư mục.
# Hiện tại, chỉ có phiên bản X86 của hệ thống Ubuntu được hỗ trợ và các hệ thống khác chưa được thử nghiệm.

# Xác định hàm xử lý ngắt
handle_interrupt() {
    echo ""
    echo "安装已被用户中断(Ctrl+C或Esc)"
    echo "如需重新安装，请再次运行脚本"
    exit 1
}

# Đặt bắt tín hiệu, xử lý Ctrl+C
trap handle_interrupt SIGINT

# Xử lý phím Esc
# Lưu cài đặt thiết bị đầu cuối
old_stty_settings=$(stty -g)
# Đặt thiết bị đầu cuối phản hồi ngay lập tức mà không có tiếng vang
stty -icanon -echo min 1 time 0

# Quá trình nền phát hiện phím Esc
(while true; do
    read -r key
    if [[ $key == $'\e' ]]; then
        # Phím Esc được phát hiện và quá trình xử lý ngắt được kích hoạt.
        kill -SIGINT $$
        break
    fi
done) &

# Khôi phục cài đặt thiết bị đầu cuối khi tập lệnh kết thúc
trap 'stty "$old_stty_settings"' EXIT


# In tranh nhân vật nhiều màu sắc
echo -e "\e[1;32m"  # 设置颜色为亮绿色
cat << "EOF"
脚本作者：@Bilibili 香草味的纳西妲喵
 __      __            _  _  _            _   _         _      _      _        
 \ \    / /           (_)| || |          | \ | |       | |    (_)    | |       
  \ \  / /__ _  _ __   _ | || |  __ _    |  \| |  __ _ | |__   _   __| |  __ _ 
   \ \/ // _` || '_ \ | || || | / _` |   | . ` | / _` || '_ \ | | / _` | / _` |
    \  /| (_| || | | || || || || (_| |   | |\  || (_| || | | || || (_| || (_| |
     \/  \__,_||_| |_||_||_||_| \__,_|   |_| \_| \__,_||_| |_||_| \__,_| \__,_|                                                                                                                                                                                                                               
EOF
echo -e "\e[0m"  # 重置颜色
echo -e "\e[1;36m  小智服务端全量部署一键安装脚本 Ver 0.2 2025年8月20日更新 \e[0m\n"
sleep 1



# Kiểm tra và cài đặt Whiptail
check_whiptail() {
    if ! command -v whiptail &> /dev/null; then
        echo "正在安装whiptail..."
        apt update
        apt install -y whiptail
    fi
}

check_whiptail

# Tạo hộp thoại xác nhận
whiptail --title "安装确认" --yesno "即将安装小智服务端，是否继续？" \
  --yes-button "继续" --no-button "退出" 10 50

# Thực hiện các hành động dựa trên lựa chọn của người dùng
case $? in
  0)
    ;;
  1)
    exit 1
    ;;
esac

# Kiểm tra quyền root
if [ $EUID -ne 0 ]; then
    whiptail --title "权限错误" --msgbox "请使用root权限运行本脚本" 10 50
    exit 1
fi

# Kiểm tra phiên bản hệ thống
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "debian" ] && [ "$ID" != "ubuntu" ]; then
        whiptail --title "系统错误" --msgbox "该脚本只支持Debian/Ubuntu系统执行" 10 60
        exit 1
    fi
else
    whiptail --title "系统错误" --msgbox "无法确定系统版本，该脚本只支持Debian/Ubuntu系统执行" 10 60
    exit 1
fi

# Tải xuống chức năng tập tin cấu hình
check_and_download() {
    local filepath=$1
    local url=$2
    if [ ! -f "$filepath" ]; then
        if ! curl -fL --progress-bar "$url" -o "$filepath"; then
            whiptail --title "错误" --msgbox "${filepath}文件下载失败" 10 50
            exit 1
        fi
    else
        echo "${filepath}文件已存在，跳过下载"
    fi
}

# Kiểm tra xem nó đã được cài đặt chưa
check_installed() {
    # Kiểm tra xem thư mục có tồn tại và không trống không
    if [ -d "/opt/xiaozhi-server/" ] && [ "$(ls -A /opt/xiaozhi-server/)" ]; then
        DIR_CHECK=1
    else
        DIR_CHECK=0
    fi
    
    # Kiểm tra xem container có tồn tại không
    if docker inspect xiaozhi-esp32-server > /dev/null 2>&1; then
        CONTAINER_CHECK=1
    else
        CONTAINER_CHECK=0
    fi
    
    # Đã vượt qua cả hai lần kiểm tra
    if [ $DIR_CHECK -eq 1 ] && [ $CONTAINER_CHECK -eq 1 ]; then
        return 0  # 已安装
    else
        return 1  # 未安装
    fi
}

# Cập nhật liên quan
if check_installed; then
    if whiptail --title "已安装检测" --yesno "检测到小智服务端已安装，是否进行升级？" 10 60; then
        # Người dùng lựa chọn nâng cấp và thực hiện thao tác dọn dẹp
        echo "开始升级操作..."
        
        # Dừng và xóa tất cả các dịch vụ docker-compose
        docker compose -f /opt/xiaozhi-server/docker-compose_all.yml down
        
        # Dừng và xóa một container cụ thể (xem xét trường hợp container có thể không tồn tại)
        containers=(
            "xiaozhi-esp32-server"
            "xiaozhi-esp32-server-web"
            "xiaozhi-esp32-server-db"
            "xiaozhi-esp32-server-redis"
        )
        
        for container in "${containers[@]}"; do
            if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
                docker stop "$container" >/dev/null 2>&1 && \
                docker rm "$container" >/dev/null 2>&1 && \
                echo "成功移除容器: $container"
            else
                echo "容器不存在，跳过: $container"
            fi
        done
        
        # Xóa một hình ảnh cụ thể (coi như hình ảnh đó có thể không tồn tại)
        images=(
            "ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:server_latest"
            "ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:web_latest"
        )
        
        for image in "${images[@]}"; do
            if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${image}$"; then
                docker rmi "$image" >/dev/null 2>&1 && \
                echo "成功删除镜像: $image"
            else
                echo "镜像不存在，跳过: $image"
            fi
        done
        
        echo "所有清理操作完成"
        
        # Sao lưu tập tin cấu hình gốc
        mkdir -p /opt/xiaozhi-server/backup/
        if [ -f /opt/xiaozhi-server/data/.config.yaml ]; then
            cp /opt/xiaozhi-server/data/.config.yaml /opt/xiaozhi-server/backup/.config.yaml
            echo "已备份原有配置文件到 /opt/xiaozhi-server/backup/.config.yaml"
        fi
        
        # Tải file cấu hình mới nhất
        check_and_download "/opt/xiaozhi-server/docker-compose_all.yml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/refs/heads/main/main/xiaozhi-server/docker-compose_all.yml"
        check_and_download "/opt/xiaozhi-server/data/.config.yaml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/refs/heads/main/main/xiaozhi-server/config_from_api.yaml"
        
        # Bắt đầu dịch vụ Docker
        echo "开始启动最新版本服务..."
        # Đánh dấu sau khi nâng cấp xong để bỏ qua các bước tải tiếp theo
        UPGRADE_COMPLETED=1
        docker compose -f /opt/xiaozhi-server/docker-compose_all.yml up -d
    else
          whiptail --title "跳过升级" --msgbox "已取消升级，将继续使用当前版本。" 10 50
          # Bỏ qua nâng cấp và tiếp tục quá trình cài đặt tiếp theo
    fi
fi


# Kiểm tra cài đặt cuộn tròn
if ! command -v curl &> /dev/null; then
    echo "------------------------------------------------------------"
    echo "未检测到curl，正在安装..."
    apt update
    apt install -y curl
else
    echo "------------------------------------------------------------"
    echo "curl已安装，跳过安装步骤"
fi

# Kiểm tra cài đặt Docker
if ! command -v docker &> /dev/null; then
    echo "------------------------------------------------------------"
    echo "未检测到Docker，正在安装..."
    
    # Sử dụng nguồn gương trong nước thay vì nguồn chính thống
    DISTRO=$(lsb_release -cs)
    MIRROR_URL="https://mirrors.aliyun.com/docker-ce/linux/ubuntu"
    GPG_URL="https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg"
    
    # Cài đặt các phụ thuộc cơ bản
    apt update
    apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg
    
    # Tạo thư mục key và thêm key nguồn ảnh trong nước
    mkdir -p /etc/apt/keyrings
    curl -fsSL "$GPG_URL" | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Thêm nguồn gương trong nước
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] $MIRROR_URL $DISTRO stable" \
        > /etc/apt/sources.list.d/docker.list
    
    # Thêm khóa nguồn chính thức thay thế (để tránh lỗi xác minh khóa nguồn trong nước)
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 7EA0A9C3F273FCD8 2>/dev/null || \
    echo "警告：部分密钥添加失败，继续尝试安装..."
    
    # Cài đặt Docker
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io
    
    # Bắt đầu dịch vụ
    systemctl start docker
    systemctl enable docker
    
    # Kiểm tra xem cài đặt có thành công không
    if docker --version; then
        echo "------------------------------------------------------------"
        echo "Docker安装完成！"
    else
        whiptail --title "错误" --msgbox "Docker安装失败，请检查日志。" 10 50
        exit 1
    fi
else
    echo "Docker已安装，跳过安装步骤"
fi

# Cấu hình nguồn hình ảnh Docker
MIRROR_OPTIONS=(
    "1" "轩辕镜像 (推荐)"
    "2" "腾讯云镜像源"
    "3" "中科大镜像源"
    "4" "网易163镜像源"
    "5" "华为云镜像源"
    "6" "阿里云镜像源"
    "7" "自定义镜像源"
    "8" "跳过配置"
)

MIRROR_CHOICE=$(whiptail --title "选择Docker镜像源" --menu "请选择要使用的Docker镜像源" 20 60 10 \
"${MIRROR_OPTIONS[@]}" 3>&1 1>&2 2>&3) || {
    echo "用户取消选择，退出脚本"
    exit 1
}

case $MIRROR_CHOICE in
    1) MIRROR_URL="https://docker.xuanyuan.me" ;; 
    2) MIRROR_URL="https://mirror.ccs.tencentyun.com" ;; 
    3) MIRROR_URL="https://docker.mirrors.ustc.edu.cn" ;; 
    4) MIRROR_URL="https://hub-mirror.c.163.com" ;; 
    5) MIRROR_URL="https://05f073ad3c0010ea0f4bc00b7105ec20.mirror.swr.myhuaweicloud.com" ;; 
    6) MIRROR_URL="https://registry.aliyuncs.com" ;; 
    7) MIRROR_URL=$(whiptail --title "自定义镜像源" --inputbox "请输入完整的镜像源URL:" 10 60 3>&1 1>&2 2>&3) ;; 
    8) MIRROR_URL="" ;; 
esac

if [ -n "$MIRROR_URL" ]; then
    mkdir -p /etc/docker
    if [ -f /etc/docker/daemon.json ]; then
        cp /etc/docker/daemon.json /etc/docker/daemon.json.bak
    fi
    cat > /etc/docker/daemon.json <<EOF
{
    "dns": ["8.8.8.8", "114.114.114.114"],
    "registry-mirrors": ["$MIRROR_URL"]
}
EOF
    whiptail --title "配置成功" --msgbox "已成功添加镜像源: $MIRROR_URL\n请按Enter键重启Docker服务并继续..." 12 60
    echo "------------------------------------------------------------"
    echo "开始重启Docker服务..."
    systemctl restart docker.service
fi

# Tạo thư mục cài đặt
echo "------------------------------------------------------------"
echo "开始创建安装目录..."
# Kiểm tra và tạo thư mục dữ liệu
if [ ! -d /opt/xiaozhi-server/data ]; then
    mkdir -p /opt/xiaozhi-server/data
    echo "已创建数据目录: /opt/xiaozhi-server/data"
else
    echo "目录xiaozhi-server/data已存在，跳过创建"
fi

# Kiểm tra và tạo danh mục mô hình
if [ ! -d /opt/xiaozhi-server/models/SenseVoiceSmall ]; then
    mkdir -p /opt/xiaozhi-server/models/SenseVoiceSmall
    echo "已创建模型目录: /opt/xiaozhi-server/models/SenseVoiceSmall"
else
    echo "目录xiaozhi-server/models/SenseVoiceSmall已存在，跳过创建"
fi

echo "------------------------------------------------------------"
echo "开始下载语音识别模型"
# Tải xuống tập tin mô hình
MODEL_PATH="/opt/xiaozhi-server/models/SenseVoiceSmall/model.pt"
if [ ! -f "$MODEL_PATH" ]; then
    (
    for i in {1..20}; do
        echo $((i*5))
        sleep 0.5
    done
    ) | whiptail --title "下载中" --gauge "开始下载语音识别模型..." 10 60 0
    curl -fL --progress-bar https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt -o "$MODEL_PATH" || {
        whiptail --title "错误" --msgbox "model.pt文件下载失败" 10 50
        exit 1
    }
else
    echo "model.pt文件已存在，跳过下载"
fi

# Nếu quá trình nâng cấp chưa hoàn tất, quá trình tải xuống sẽ được thực hiện.
if [ -z "$UPGRADE_COMPLETED" ]; then
    check_and_download "/opt/xiaozhi-server/docker-compose_all.yml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/refs/heads/main/main/xiaozhi-server/docker-compose_all.yml"
    check_and_download "/opt/xiaozhi-server/data/.config.yaml" "https://ghfast.top/https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/refs/heads/main/main/xiaozhi-server/config_from_api.yaml"
fi

# Bắt đầu dịch vụ Docker
(
echo "------------------------------------------------------------"
echo "正在拉取Docker镜像..."
echo "这可能需要几分钟时间，请耐心等待"
docker compose -f /opt/xiaozhi-server/docker-compose_all.yml up -d

if [ $? -ne 0 ]; then
    whiptail --title "错误" --msgbox "Docker服务启动失败，请尝试更换镜像源后重新执行本脚本" 10 60
    exit 1
fi

echo "------------------------------------------------------------"
echo "正在检查服务启动状态..."
TIMEOUT=300
START_TIME=$(date +%s)
while true; do
    CURRENT_TIME=$(date +%s)
    if [ $((CURRENT_TIME - START_TIME)) -gt $TIMEOUT ]; then
        whiptail --title "错误" --msgbox "服务启动超时，未在指定时间内找到预期日志内容" 10 60
        exit 1
    fi
    
    if docker logs xiaozhi-esp32-server-web 2>&1 | grep -q "Started AdminApplication in"; then
        break
    fi
    sleep 1
done

    echo "服务端启动成功！正在完成配置..."
    echo "正在启动服务..."
    docker compose -f /opt/xiaozhi-server/docker-compose_all.yml up -d
    echo "服务启动完成！"
)

# Cấu hình khóa

# Lấy địa chỉ mạng công cộng của máy chủ
PUBLIC_IP=$(hostname -I | awk '{print $1}')
whiptail --title "配置服务器密钥" --msgbox "请使用浏览器，访问下方链接，打开智控台并注册账号: \n\n内网地址：http://127.0.0.1:8002/\n公网地址：http://$PUBLIC_IP:8002/ (若是云服务器请在服务器安全组放行端口 8000 8001 8002)。\n\n注册的第一个用户即是超级管理员，以后注册的用户都是普通用户。普通用户只能绑定设备和配置智能体; 超级管理员可以进行模型管理、用户管理、参数配置等功能。\n\n注册好后请按Enter键继续" 18 70
SECRET_KEY=$(whiptail --title "配置服务器密钥" --inputbox "请使用超级管理员账号登录智控台\n内网地址：http://127.0.0.1:8002/\n公网地址：http://$PUBLIC_IP:8002/\n在顶部菜单 参数字典 → 参数管理 找到参数编码: server.secret (服务器密钥) \n复制该参数值并输入到下面输入框\n\n请输入密钥(留空则跳过配置):" 15 60 3>&1 1>&2 2>&3)

if [ -n "$SECRET_KEY" ]; then
    python3 -c "
import sys, yaml; 
config_path = '/opt/xiaozhi-server/data/.config.yaml'; 
with open(config_path, 'r') as f: 
    config = yaml.safe_load(f) or {}; 
config['manager-api'] = {'url': 'http://xiaozhi-esp32-server-web:8002/xiaozhi', 'secret': '$SECRET_KEY'}; 
with open(config_path, 'w') as f: 
    yaml.dump(config, f); 
"
    docker restart xiaozhi-esp32-server
fi

# Nhận và hiển thị thông tin địa chỉ
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Đã khắc phục sự cố tệp nhật ký không thể lấy được ws và thay đổi nó thành mã hóa cứng.
whiptail --title "安装完成！" --msgbox "\
服务端相关地址如下：\n\
管理后台访问地址: http://$LOCAL_IP:8002\n\
OTA 地址: http://$LOCAL_IP:8002/xiaozhi/ota/\n\
视觉分析接口地址: http://$LOCAL_IP:8003/mcp/vision/explain\n\
WebSocket 地址: ws://$LOCAL_IP:8000/xiaozhi/v1/\n\
\n安装完毕！感谢您的使用！\n按Enter键退出..." 16 70
