package xiaozhi.common.exception;

/**
 * Mã lỗi bao gồm 5 chữ số. 2 chữ số đầu là mã module và 3 chữ số cuối là mã doanh nghiệp.
 * <p>
 * Ví dụ: 10001 (10 tượng trưng cho mô-đun hệ thống, 001 tượng trưng cho mã doanh nghiệp)
 * </p>
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
public interface ErrorCode {
    int INTERNAL_SERVER_ERROR = 500;
    int UNAUTHORIZED = 401;
    int FORBIDDEN = 403;

    int NOT_NULL = 10001;
    int DB_RECORD_EXISTS = 10002;
    int PARAMS_GET_ERROR = 10003;
    int ACCOUNT_PASSWORD_ERROR = 10004;
    int ACCOUNT_DISABLE = 10005;
    int IDENTIFIER_NOT_NULL = 10006;
    int CAPTCHA_ERROR = 10007;
    int PHONE_NOT_NULL = 10008;
    int PASSWORD_ERROR = 10009;

    int SUPERIOR_DEPT_ERROR = 10011;
    int SUPERIOR_MENU_ERROR = 10012;
    int DATA_SCOPE_PARAMS_ERROR = 10013;
    int DEPT_SUB_DELETE_ERROR = 10014;
    int DEPT_USER_DELETE_ERROR = 10015;

    int UPLOAD_FILE_EMPTY = 10019;
    int TOKEN_NOT_EMPTY = 10020;
    int TOKEN_INVALID = 10021;
    int ACCOUNT_LOCK = 10022;

    int OSS_UPLOAD_FILE_ERROR = 10024;

    int REDIS_ERROR = 10027;
    int JOB_ERROR = 10028;
    int INVALID_SYMBOL = 10029;
    int PASSWORD_LENGTH_ERROR = 10030;
    int PASSWORD_WEAK_ERROR = 10031;
    int DEL_MYSELF_ERROR = 10032;
    int DEVICE_CAPTCHA_ERROR = 10033;

    // Mã lỗi liên quan đến xác minh tham số
    int PARAM_VALUE_NULL = 10034;
    int PARAM_TYPE_NULL = 10035;
    int PARAM_TYPE_INVALID = 10036;
    int PARAM_NUMBER_INVALID = 10037;
    int PARAM_BOOLEAN_INVALID = 10038;
    int PARAM_ARRAY_INVALID = 10039;
    int PARAM_JSON_INVALID = 10040;

    int OTA_DEVICE_NOT_FOUND = 10041;
    int OTA_DEVICE_NEED_BIND = 10042;

    // Đã thêm mã lỗi
    int DELETE_DATA_FAILED = 10043;
    int USER_NOT_LOGIN = 10044;
    int WEB_SOCKET_CONNECT_FAILED = 10045;
    int VOICE_PRINT_SAVE_ERROR = 10046;
    int TODAY_SMS_LIMIT_REACHED = 10047;
    int OLD_PASSWORD_ERROR = 10048;
    int INVALID_LLM_TYPE = 10049;
    int TOKEN_GENERATE_ERROR = 10050;
    int RESOURCE_NOT_FOUND = 10051;

    // Đã thêm mã lỗi
    int DEFAULT_AGENT_NOT_FOUND = 10052;
    int AGENT_NOT_FOUND = 10053;
    int VOICEPRINT_API_NOT_CONFIGURED = 10054;
    int SMS_SEND_FAILED = 10055;
    int SMS_CONNECTION_FAILED = 10056;
    int AGENT_VOICEPRINT_CREATE_FAILED = 10057;
    int AGENT_VOICEPRINT_UPDATE_FAILED = 10058;
    int AGENT_VOICEPRINT_DELETE_FAILED = 10059;
    int SMS_SEND_TOO_FREQUENTLY = 10060;
    int ACTIVATION_CODE_EMPTY = 10061;
    int ACTIVATION_CODE_ERROR = 10062;
    int DEVICE_ALREADY_ACTIVATED = 10063;
    // Lỗi xóa mô hình mặc định
    int DEFAULT_MODEL_DELETE_ERROR = 10064;
    // Mã lỗi liên quan đến đăng nhập
    int ADD_DATA_FAILED = 10065; // Không thể thêm dữ liệu
    int UPDATE_DATA_FAILED = 10066; // Không thể sửa đổi dữ liệu
    int SMS_CAPTCHA_ERROR = 10067; // Lỗi mã xác minh SMS
    int MOBILE_REGISTER_DISABLED = 10068; // Đăng ký điện thoại di động không được kích hoạt
    int USERNAME_NOT_PHONE = 10069; // Tên người dùng không phải là số điện thoại di động
    int PHONE_ALREADY_REGISTERED = 10070; // Số điện thoại di động đã được đăng ký
    int PHONE_NOT_REGISTERED = 10071; // Số điện thoại di động chưa được đăng ký
    int USER_REGISTER_DISABLED = 10072; // Đăng ký người dùng không được phép
    int RETRIEVE_PASSWORD_DISABLED = 10073; // Chức năng lấy lại mật khẩu chưa được kích hoạt
    int PHONE_FORMAT_ERROR = 10074; // Định dạng số điện thoại di động không chính xác
    int SMS_CODE_ERROR = 10075; // Lỗi mã xác minh điện thoại di động

    // Mã lỗi liên quan đến loại từ điển
    int DICT_TYPE_NOT_EXIST = 10076; // Loại từ điển không tồn tại
    int DICT_TYPE_DUPLICATE = 10077; // Mã hóa kiểu từ điển trùng lặp

    // Mã lỗi liên quan đến xử lý tài nguyên
    int RESOURCE_READ_ERROR = 10078; // Không đọc được tài nguyên

    // Mã lỗi liên quan đến đại lý
    int LLM_INTENT_PARAMS_MISMATCH = 10079; // Mô hình LLM lớn và nhận dạng Intent, các tham số lựa chọn không khớp

    // Mã lỗi liên quan đến giọng nói
    int VOICEPRINT_ALREADY_REGISTERED = 10080; // Giọng nói này đã được đăng ký
    int VOICEPRINT_DELETE_ERROR = 10081; // Đã xảy ra lỗi khi xóa giọng nói
    int VOICEPRINT_UPDATE_NOT_ALLOWED = 10082; // Không được phép sửa đổi giọng nói, giọng nói đã được đăng ký
    int VOICEPRINT_UPDATE_ADMIN_ERROR = 10083; // Để sửa lỗi in giọng nói, vui lòng liên hệ với quản trị viên.
    int VOICEPRINT_API_URI_ERROR = 10084; // Lỗi địa chỉ giao diện Voiceprint
    int VOICEPRINT_AUDIO_NOT_BELONG_AGENT = 10085; // Dữ liệu âm thanh không thuộc về tác nhân
    int VOICEPRINT_AUDIO_EMPTY = 10086; // Dữ liệu âm thanh trống
    int VOICEPRINT_REGISTER_REQUEST_ERROR = 10087; // Yêu cầu lưu giọng nói không thành công
    int VOICEPRINT_REGISTER_PROCESS_ERROR = 10088; // Quá trình lưu giọng nói không thành công
    int VOICEPRINT_UNREGISTER_REQUEST_ERROR = 10089; // Yêu cầu đăng xuất bằng giọng nói không thành công
    int VOICEPRINT_UNREGISTER_PROCESS_ERROR = 10090; // Xử lý đăng xuất bằng giọng nói không thành công
    int VOICEPRINT_IDENTIFY_REQUEST_ERROR = 10091; // Yêu cầu nhận dạng giọng nói không thành công

    int LLM_NOT_EXIST = 10092; // Bộ LLM không tồn tại
    int MODEL_REFERENCED_BY_AGENT = 10093; // Cấu hình mô hình đã được tác nhân tham chiếu và không thể xóa được
    int LLM_REFERENCED_BY_INTENT = 10094; // Mô hình LLM này đã được cấu hình nhận dạng ý định tham chiếu và không thể xóa được.

    // Mã lỗi liên quan đến quản lý máy chủ
    int INVALID_SERVER_ACTION = 10095; // Hoạt động của máy chủ không hợp lệ
    int SERVER_WEBSOCKET_NOT_CONFIGURED = 10096; // Địa chỉ WebSocket của máy chủ chưa được định cấu hình
    int TARGET_WEBSOCKET_NOT_EXIST = 10097; // Địa chỉ WebSocket mục tiêu không tồn tại

    // Mã lỗi liên quan đến xác minh tham số
    int WEBSOCKET_URLS_EMPTY = 10098; // Danh sách địa chỉ WebSocket không được để trống
    int WEBSOCKET_URL_LOCALHOST = 10099; // Địa chỉ WebSocket không thể sử dụng localhost hoặc 127.0.0.1
    int WEBSOCKET_URL_FORMAT_ERROR = 10100; // Định dạng địa chỉ WebSocket không chính xác
    int WEBSOCKET_CONNECTION_FAILED = 10101; // Kiểm tra kết nối WebSocket không thành công
    int OTA_URL_EMPTY = 10102; // Địa chỉ OTA không được để trống
    int OTA_URL_LOCALHOST = 10103; // Địa chỉ OTA không thể sử dụng localhost hoặc 127.0.0.1
    int OTA_URL_PROTOCOL_ERROR = 10104; // Địa chỉ OTA phải bắt đầu bằng http hoặc https
    int OTA_URL_FORMAT_ERROR = 10105; // Địa chỉ OTA phải kết thúc bằng /ota/
    int OTA_INTERFACE_ACCESS_FAILED = 10106; // Truy cập giao diện OTA không thành công
    int OTA_INTERFACE_FORMAT_ERROR = 10107; // Định dạng nội dung được giao diện OTA trả về không chính xác
    int OTA_INTERFACE_VALIDATION_FAILED = 10108; // Xác minh giao diện OTA không thành công
    int MCP_URL_EMPTY = 10109; // Địa chỉ MCP không được để trống
    int MCP_URL_LOCALHOST = 10110; // Địa chỉ MCP không thể sử dụng localhost hoặc 127.0.0.1
    int MCP_URL_INVALID = 10111; // Địa chỉ MCP không chính xác
    int MCP_INTERFACE_ACCESS_FAILED = 10112; // Truy cập giao diện MCP không thành công
    int MCP_INTERFACE_FORMAT_ERROR = 10113; // Định dạng của nội dung được giao diện MCP trả về không chính xác
    int MCP_INTERFACE_VALIDATION_FAILED = 10114; // Xác minh giao diện MCP không thành công
    int VOICEPRINT_URL_EMPTY = 10115; // Địa chỉ giao diện giọng nói không được để trống.
    int VOICEPRINT_URL_LOCALHOST = 10116; // Địa chỉ giao diện voiceprint không thể sử dụng localhost hoặc 127.0.0.1
    int VOICEPRINT_URL_INVALID = 10117; // Địa chỉ giao diện giọng nói không chính xác
    int VOICEPRINT_URL_PROTOCOL_ERROR = 10118; // Địa chỉ giao diện giọng nói phải bắt đầu bằng http hoặc https
    int VOICEPRINT_INTERFACE_ACCESS_FAILED = 10119; // Truy cập giao diện giọng nói không thành công
    int VOICEPRINT_INTERFACE_FORMAT_ERROR = 10120; // Định dạng nội dung được giao diện giọng nói trả về không chính xác.
    int VOICEPRINT_INTERFACE_VALIDATION_FAILED = 10121; // Xác minh giao diện giọng nói không thành công
    int MQTT_SECRET_EMPTY = 10122; // khóa mqtt không được để trống
    int MQTT_SECRET_LENGTH_INSECURE = 10123; // độ dài khóa mqtt không an toàn
    int MQTT_SECRET_CHARACTER_INSECURE = 10124; // khóa mqtt phải chứa cả chữ hoa và chữ thường
    int MQTT_SECRET_WEAK_PASSWORD = 10125; // khóa mqtt chứa mật khẩu yếu
    int DICT_LABEL_DUPLICATE = 10128; // Thẻ từ điển trùng lặp
    int SM2_KEY_NOT_CONFIGURED = 10129; // Khóa SM2 chưa được cấu hình
    int SM2_DECRYPT_ERROR = 10130; // Giải mã SM2 không thành công
    int MODEL_TYPE_PROVIDE_CODE_NOT_NULL = 10131; // modelType và cung cấpCode không được để trống

    // Mã lỗi liên quan đến lịch sử trò chuyện
    int CHAT_HISTORY_NO_PERMISSION = 10132; // Không có quyền xem lịch sử trò chuyện của đại lý này
    int CHAT_HISTORY_SESSION_ID_NOT_NULL = 10133; // ID phiên không thể trống
    int CHAT_HISTORY_AGENT_ID_NOT_NULL = 10134; // ID đại lý không được để trống
    int CHAT_HISTORY_DOWNLOAD_FAILED = 10135; // Tải xuống lịch sử trò chuyện không thành công
    int DOWNLOAD_LINK_EXPIRED = 10136; // Liên kết tải xuống đã hết hạn hoặc không hợp lệ
    int DOWNLOAD_LINK_INVALID = 10137; // Liên kết tải xuống không hợp lệ
    int CHAT_ROLE_USER = 10138; // vai trò người dùng
    int CHAT_ROLE_AGENT = 10139; // vai trò đại lý

    // Mã lỗi liên quan đến nhân bản âm thanh
    int VOICE_CLONE_AUDIO_EMPTY = 10140; // Tệp âm thanh không thể trống
    int VOICE_CLONE_NOT_AUDIO_FILE = 10141; // Chỉ hỗ trợ tập tin âm thanh
    int VOICE_CLONE_AUDIO_TOO_LARGE = 10142; // Kích thước tệp âm thanh không được vượt quá 10MB
    int VOICE_CLONE_UPLOAD_FAILED = 10143; // Tải lên không thành công
    int VOICE_CLONE_RECORD_NOT_EXIST = 10144; // Bản ghi bản sao âm thanh không tồn tại
    int VOICE_RESOURCE_INFO_EMPTY = 10145; // Thông tin tài nguyên giai điệu không được để trống
    int VOICE_RESOURCE_PLATFORM_NAME_EMPTY = 10146; // Tên nền tảng không được để trống
    int VOICE_RESOURCE_ID_EMPTY = 10147; // ID giai điệu không được để trống
    int VOICE_RESOURCE_ACCOUNT_EMPTY = 10148; // Tài khoản được phân bổ không được để trống
    int VOICE_RESOURCE_DELETE_ID_EMPTY = 10149; // ID tài nguyên âm thanh đã xóa không được để trống.
    int VOICE_RESOURCE_NO_PERMISSION = 10150; // Bạn không có quyền vận hành bản ghi này
    int VOICE_CLONE_AUDIO_NOT_UPLOADED = 10151; // Vui lòng tải lên tệp âm thanh trước
    int VOICE_CLONE_MODEL_CONFIG_NOT_FOUND = 10152; // Không tìm thấy cấu hình mô hình
    int VOICE_CLONE_MODEL_TYPE_NOT_FOUND = 10153; // Không tìm thấy loại mô hình
    int VOICE_CLONE_TRAINING_FAILED = 10154; // Đào tạo không thành công
    int VOICE_CLONE_HUOSHAN_CONFIG_MISSING = 10155; // Động cơ núi lửa thiếu cấu hình
    int VOICE_CLONE_RESPONSE_FORMAT_ERROR = 10156; // Lỗi định dạng phản hồi
    int VOICE_CLONE_REQUEST_FAILED = 10157; // Yêu cầu không thành công
    int VOICE_CLONE_PREFIX = 10158; // Tiền tố giai điệu sao chép
    int VOICE_ID_ALREADY_EXISTS = 10159; // ID giai điệu đã tồn tại
    int VOICE_CLONE_HUOSHAN_VOICE_ID_ERROR = 10160; // Lỗi định dạng ID âm thanh động cơ núi lửa

    // Mã lỗi liên quan đến thiết bị
    int MAC_ADDRESS_ALREADY_EXISTS = 10161; // Địa chỉ Mac đã tồn tại
    // Mã lỗi liên quan đến mô hình
    int MODEL_PROVIDER_NOT_EXIST = 10162; // nhà cung cấp không tồn tại

    // Mã lỗi liên quan đến cơ sở kiến thức
    int Knowledge_Base_RECORD_NOT_EXISTS = 10163; // Bản ghi cơ sở kiến thức không tồn tại
    int RAG_CONFIG_NOT_FOUND = 10164; // Không tìm thấy cấu hình RAG
    int RAG_CONFIG_TYPE_ERROR = 10165; // Lỗi loại cấu hình RAG
    int RAG_DEFAULT_CONFIG_NOT_FOUND = 10166; // Không tìm thấy cấu hình RAG mặc định
    int RAG_API_ERROR = 10167; // Cuộc gọi RAG không thành công
    int UPLOAD_FILE_ERROR = 10168; // Tải tệp lên không thành công
    int NO_PERMISSION = 10169; // Không có sự cho phép
    int KNOWLEDGE_BASE_NAME_EXISTS = 10170; // Đã tồn tại cơ sở kiến thức có cùng tên
    int RAG_API_ERROR_URL_NULL = 10171; // base_url trong cấu hình RAG trống, vui lòng hoàn tất cấu hình.
    int RAG_API_ERROR_API_KEY_NULL = 10172; // Api_key trong cấu hình RAG trống, vui lòng hoàn tất cấu hình.
    int RAG_API_ERROR_API_KEY_INVALID = 10173; // api_key trong cấu hình RAG chứa phần giữ chỗ, vui lòng thay thế nó bằng khóa API thực tế
    int RAG_API_ERROR_URL_INVALID = 10174; // Định dạng của base_url trong cấu hình RAG không chính xác, vui lòng kiểm tra xem giao thức có đúng không
    int RAG_DATASET_ID_NOT_NULL = 10176; // tập dữ liệu_id trong cấu hình RAG không được để trống
    int RAG_MODEL_ID_NOT_NULL = 10177; // model_id trong cấu hình RAG không được để trống
    int RAG_DATASET_ID_AND_MODEL_ID_NOT_NULL = 10178; // tập dữ liệu_id và model_id trong cấu hình RAG không được để trống
    int RAG_FILE_NAME_NOT_NULL = 10179; // Tên tệp không được để trống
    int RAG_FILE_CONTENT_EMPTY = 10180; // Nội dung tập tin không thể trống

    // Mã lỗi liên quan đến thiết bị (bổ sung)
    int MCA_NOT_NULL = 10175; // địa chỉ mac không được để trống

    // Nhân bản giai điệu (Bổ sung)
    int VOICE_CLONE_NAME_NOT_NULL = 10181; // Tên bản sao âm thanh không được để trống
    int VOICE_CLONE_AUDIO_NOT_FOUND = 10182; // Âm thanh nhân bản âm thanh không tồn tại

    // Mã lỗi liên quan đến mẫu đại lý (bổ sung)
    int AGENT_TEMPLATE_NOT_FOUND = 10183; // Không tìm thấy tác nhân mặc định

    // Mã lỗi liên quan đến bộ điều hợp cơ sở kiến thức
    int RAG_ADAPTER_TYPE_NOT_SUPPORTED = 10184; // Loại bộ chuyển đổi không được hỗ trợ
    int RAG_CONFIG_VALIDATION_FAILED = 10185; // Xác minh cấu hình RAG không thành công
    int RAG_ADAPTER_CREATION_FAILED = 10186; // Tạo bộ chuyển đổi không thành công
    int RAG_ADAPTER_INIT_FAILED = 10187; // Khởi tạo bộ điều hợp không thành công
    int RAG_ADAPTER_CONNECTION_FAILED = 10188; // Kiểm tra kết nối bộ chuyển đổi không thành công
    int RAG_ADAPTER_OPERATION_FAILED = 10189; // Thao tác bộ chuyển đổi không thành công
    int RAG_ADAPTER_NOT_FOUND = 10190; // Không tìm thấy bộ chuyển đổi
    int RAG_ADAPTER_CACHE_ERROR = 10191; // Lỗi bộ nhớ đệm của bộ điều hợp
    int RAG_ADAPTER_TYPE_NOT_FOUND = 10192; // Không tìm thấy loại bộ điều hợp

    // Mã lỗi liên quan đến công cụ thiết bị
    int DEVICE_ID_NOT_NULL = 10193; // ID thiết bị không được để trống
    int DEVICE_NOT_EXIST = 10194; // Thiết bị không tồn tại
    int OTA_UPLOAD_COUNT_EXCEED = 10195; // Số lượng tải lên OTA vượt quá giới hạn

    // Mã lỗi liên quan đến thẻ đại lý
    int AGENT_TAG_NAME_DUPLICATE = 10196; // Tên thẻ đã tồn tại
    int AGENT_TAG_NAME_EMPTY = 10197; // Tên thẻ không được để trống
    int AGENT_TAG_NOT_EXIST = 10198; // Thẻ không tồn tại

    int RAG_DOCUMENT_PARSING_DELETE_ERROR = 10199; // Trong quá trình phân tích tài liệu, việc xóa bị cấm

    // Mã lỗi liên quan đến đại lý MCP
    int MCP_ACCESS_POINT_ADDRESS_NO_PERMISSION = 10200; // Bạn không có quyền xem địa chỉ điểm truy cập MCP của tác nhân này.
    int MCP_ACCESS_POINT_ADDRESS_NOT_CONFIGURED = 10201; // Vui lòng liên hệ với quản trị viên để nhập quản lý tham số nhằm định cấu hình địa chỉ điểm truy cập mcp.
    int MCP_ACCESS_POINT_TOOLS_LIST_NO_PERMISSION = 10202; // Bạn không có quyền xem danh sách công cụ MCP của tác nhân này.

    // Mã lỗi liên quan đến từ thay thế
    int CORRECT_WORD_FILE_NAME_EXISTS = 10203; // tên tập tin đã tồn tại
    int FILE_SIZE_OVER_LIMIT = 10204; // Kích thước tệp vượt quá giới hạn
}
