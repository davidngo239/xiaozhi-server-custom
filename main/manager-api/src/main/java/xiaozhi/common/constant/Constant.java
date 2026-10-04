package xiaozhi.common.constant;

import lombok.Getter;

/**
 * hằng số
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
public interface Constant {
    /**
     * sự thành công
     */
    int SUCCESS = 1;
    /**
     * thất bại
     */
    int FAIL = 0;
    /**
     * OK
     */
    String OK = "OK";
    /**
     * ID người dùng
     */
    String USER_KEY = "userId";
    /**
     * Mã định danh nút gốc của menu
     */
    Long MENU_ROOT = 0L;
    /**
     * ID nút gốc của bộ phận
     */
    Long DEPT_ROOT = 0L;
    /**
     * Mã định danh nút gốc của từ điển dữ liệu
     */
    Long DICT_ROOT = 0L;
    /**
     * Thứ tự tăng dần
     */
    String ASC = "asc";
    /**
     * thứ tự giảm dần
     */
    String DESC = "desc";
    /**
     * Tên trường thời gian tạo
     */
    String CREATE_DATE = "create_date";

    /**
     * Tên trường thời gian tạo
     */
    String ID = "id";

    /**
     * Lọc quyền dữ liệu
     */
    String SQL_FILTER = "sqlFilter";

    /**
     * Số trang hiện tại
     */
    String PAGE = "page";
    /**
     * Hiển thị số bản ghi trên mỗi trang
     */
    String LIMIT = "limit";
    /**
     * trường sắp xếp
     */
    String ORDER_FIELD = "orderField";
    /**
     * Sắp xếp theo
     */
    String ORDER = "order";

    /**
     * Yêu cầu mã định danh ủy quyền tiêu đề
     */
    String AUTHORIZATION = "Authorization";

    /**
     * khóa máy chủ
     */
    String SERVER_SECRET = "server.secret";

    /**
     * Khóa công khai SM2
     */
    String SM2_PUBLIC_KEY = "server.public_key";

    /**
     * Khóa riêng SM2
     */
    String SM2_PRIVATE_KEY = "server.private_key";

    /**
     * địa chỉ websocket
     */
    String SERVER_WEBSOCKET = "server.websocket";

    /**
     * cấu hình cổng mqtt
     */
    String SERVER_MQTT_GATEWAY = "server.mqtt_gateway";

    /**
     * địa chỉ ota
     */
    String SERVER_OTA = "server.ota";

    /**
     * Có cho phép đăng ký người dùng hay không
     */
    String SERVER_ALLOW_USER_REGISTER = "server.allow_user_register";

    /**
     * Địa chỉ bảng điều khiển được hiển thị khi cấp mã xác minh gồm sáu chữ số
     */
    String SERVER_FRONTED_URL = "server.fronted_url";

    /**
     * dấu phân cách đường dẫn
     */
    String FILE_EXTENSION_SEG = ".";

    /**
     * đường dẫn điểm truy cập mcp
     */
    String SERVER_MCP_ENDPOINT = "server.mcp_endpoint";

    /**
     * đường dẫn điểm truy cập mcp
     */
    String SERVER_VOICE_PRINT = "server.voice_print";

    /**
     * khóa mqtt
     */
    String SERVER_MQTT_SECRET = "server.mqtt_signature_key";

    /**
     * Công tắc xác thực WebSocket
     */
    String SERVER_AUTH_ENABLED = "server.auth.enabled";

    /**
     * Cấu hình menu chức năng hệ thống
     */
    String SYSTEM_WEB_MENU = "system-web.menu";

    /**
     * không có trí nhớ
     */
    String MEMORY_NO_MEM = "Memory_nomem";

    /**
     * Chỉ báo cáo lịch sử trò chuyện (không có bộ nhớ tóm tắt)
     */
    String MEMORY_MEM_REPORT_ONLY = "Memory_mem_report_only";

    /**
     * Bộ nhớ Mem0AI
     */
    String MEMORY_MEM0AI = "Memory_mem0ai";

    /**
     * Bộ nhớ PowerMem
     */
    String MEMORY_POWERMEM = "Memory_powermem";

    /**
     * Nhân bản giọng nói hai tai của động cơ núi lửa
     */
    String VOICE_CLONE_HUOSHAN_DOUBLE_STREAM = "huoshan_double_stream";

    /**
     * Loại cấu hình RAG
     */
    String RAG_CONFIG_TYPE = "RAG";

    enum SysBaseParam {
        /**
         * Số đăng ký ICP
         */
        BEIAN_ICP_NUM("server.beian_icp_num"),
        /**
         * Số đăng ký GA
         */
        BEIAN_GA_NUM("server.beian_ga_num"),
        /**
         * Tên hệ thống
         */
        SERVER_NAME("server.name");

        private String value;

        SysBaseParam(String value) {
            this.value = value;
        }

        public String getValue() {
            return value;
        }
    }

    /**
     * tình trạng đào tạo
     */
    enum TrainStatus {
        /**
         * Không được đào tạo
         */
        NOT_TRAINED(0),
        /**
         * trong đào tạo
         */
        TRAINING(1),
        /**
         * Được đào tạo
         */
        TRAINED(2),
        /**
         * Đào tạo không thành công
         */
        TRAIN_FAILED(3);

        private final int code;

        TrainStatus(int code) {
            this.code = code;
        }

        public int getCode() {
            return code;
        }
    }

    /**
     * SMS hệ thống
     */
    enum SysMSMParam {
        /**
         * KeyID ủy quyền của Đám mây Alibaba
         */
        ALIYUN_SMS_ACCESS_KEY_ID("aliyun.sms.access_key_id"),
        /**
         * Khóa ủy quyền của Đám mây Alibaba
         */
        ALIYUN_SMS_ACCESS_KEY_SECRET("aliyun.sms.access_key_secret"),
        /**
         * Chữ ký SMS trên nền tảng đám mây của Alibaba
         */
        ALIYUN_SMS_SIGN_NAME("aliyun.sms.sign_name"),
        /**
         * Mẫu SMS trên nền tảng đám mây của Alibaba
         */
        ALIYUN_SMS_SMS_CODE_TEMPLATE_CODE("aliyun.sms.sms_code_template_code"),
        /**
         * Số lượng tin nhắn văn bản tối đa được gửi đến một số
         */
        SERVER_SMS_MAX_SEND_COUNT("server.sms_max_send_count"),
        /**
         * Có bật đăng ký điện thoại di động hay không
         */
        SERVER_ENABLE_MOBILE_REGISTER("server.enable_mobile_register");

        private String value;

        SysMSMParam(String value) {
            this.value = value;
        }

        public String getValue() {
            return value;
        }
    }

    /**
     * Trạng thái dữ liệu
     */
    enum DataOperation {
        /**
         * Chèn
         */
        INSERT("I"),
        /**
         * Đã sửa đổi
         */
        UPDATE("U"),
        /**
         * Đã xóa
         */
        DELETE("D");

        private String value;

        DataOperation(String value) {
            this.value = value;
        }

        public String getValue() {
            return value;
        }
    }

    @Getter
    enum ChatHistoryConfEnum {
        IGNORE(0, "不记录"),
        RECORD_TEXT(1, "记录文本"),
        RECORD_TEXT_AUDIO(2, "文本音频都记录");

        private final int code;
        private final String name;

        ChatHistoryConfEnum(int code, String name) {
            this.code = code;
            this.name = name;
        }
    }

    /**
     * số phiên bản
     */
    public static final String VERSION = "0.9.7";

    /**
     * URL chương trình cơ sở không hợp lệ
     */
    String INVALID_FIRMWARE_URL = "http://xiaozhi.server.com:8002/xiaozhi/otaMag/download/NOT_ACTIVATED_FIRMWARE_THIS_IS_A_INVALID_URL";

    /**
     * loại từ điển
     */
    enum DictType {
        /**
         * Mã vùng điện thoại di động
         */
        MOBILE_AREA("MOBILE_AREA");

        private String value;

        DictType(String value) {
            this.value = value;
        }

        public String getValue() {
            return value;
        }
    }
}