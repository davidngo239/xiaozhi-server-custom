package xiaozhi.common.redis;

/**
 * Lớp hằng số Redis Key
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
public class RedisKeys {
    /**
     * Khóa tham số hệ thống
     */
    public static String getSysParamsKey() {
        return "sys:params";
    }

    /**
     * Mã xác minhKey
     */
    public static String getCaptchaKey(String uuid) {
        return "sys:captcha:" + uuid;
    }

    /**
     * Mã xác minh thiết bị chưa đăng ký Key
     */
    public static String getDeviceCaptchaKey(String captcha) {
        return "sys:device:captcha:" + captcha;
    }

    /**
     * Khóa id người dùng
     */
    public static String getUserIdKey(Long userid) {
        return "sys:username:id:" + userid;
    }

    /**
     * Chìa khóa tên model
     */
    public static String getModelNameById(String id) {
        return "model:name:" + id;
    }

    /**
     * Chìa khóa cấu hình mô hình
     */
    public static String getModelConfigById(String id) {
        return "model:data:" + id;
    }

    /**
     * Lấy khóa bộ đệm tên âm sắc
     */
    public static String getTimbreNameById(String id) {
        return "timbre:name:" + id;
    }

    /**
     * Lấy key cache số thiết bị
     */
    public static String getAgentDeviceCountById(String id) {
        return "agent:device:count:" + id;
    }

    /**
     * Lấy khóa bộ đệm thời gian kết nối cuối cùng của đại lý
     */
    public static String getAgentDeviceLastConnectedAtById(String id) {
        return "agent:device:lastConnected:" + id;
    }

    /**
     * Lấy key cache cấu hình hệ thống
     */
    public static String getServerConfigKey() {
        return "server:config";
    }

    /**
     * Lấy khóa bộ nhớ đệm chi tiết âm sắc
     */
    public static String getTimbreDetailsKey(String id) {
        return "timbre:details:" + id;
    }

    /**
     * Nhận khóa số phiên bản
     */
    public static String getVersionKey() {
        return "sys:version";
    }

    /**
     * Khóa ID chương trình cơ sở OTA
     */
    public static String getOtaIdKey(String uuid) {
        return "ota:id:" + uuid;
    }

    /**
     * Key số lần tải firmware OTA
     */
    public static String getOtaDownloadCountKey(String uuid) {
        return "ota:download:count:" + uuid;
    }

    /**
     * Lấy key cache của dữ liệu từ điển
     */
    public static String getDictDataByTypeKey(String dictType) {
        return "sys:dict:data:" + dictType;
    }

    /**
     * Lấy khóa bộ đệm của ID âm thanh tác nhân
     */
    public static String getAgentAudioIdKey(String uuid) {
        return "agent:audio:id:" + uuid;
    }

    /**
     * Lấy khóa bộ đệm của mã xác minh SMS
     */
    public static String getSMSValidateCodeKey(String phone) {
        return "sms:Validate:Code:" + phone;
    }

    /**
     * Lấy khóa bộ đệm của lần gửi mã xác minh SMS gần đây nhất
     */
    public static String getSMSLastSendTimeKey(String phone) {
        return "sms:Validate:Code:" + phone + ":last_send_time";
    }

    /**
     * Lấy cache key số lượng mã xác minh SMS gửi hôm nay
     */
    public static String getSMSTodayCountKey(String phone) {
        return "sms:Validate:Code:" + phone + ":today_count";
    }

    /**
     * Khóa ánh xạ UUID của bản ghi trò chuyện
     */
    public static String getChatHistoryKey(String uuid) {
        return "agent:chat:history:" + uuid;
    }

    /**
     * Lấy khóa bộ đệm của ID âm thanh nhân bản âm sắc
     */
    public static String getVoiceCloneAudioIdKey(String uuid) {
        return "voiceClone:audio:id:" + uuid;
    }

    /**
     * Nhận khóa bộ đệm cơ sở kiến thức
     */
    public static String getKnowledgeBaseCacheKey(String datasetId) {
        return "knowledge:base:" + datasetId;
    }

    /**
     * Nhận key thẻ thiết bị đăng ký tạm thời
     */
    public static String getTmpRegisterMacKey(String deviceId) {
        return "tmp_register_mac:" + deviceId;
    }

    /**
     * Thiết bị liên kết OTA
     */
    public static String getOtaActivationCode(String activationCode) {
        return "ota:activation:code:" + activationCode;
    }

    /**
     * OTA lấy thông tin liên quan đến thiết bị mac
     */
    public static String getOtaDeviceActivationInfo(String deviceId) {
        return "ota:activation:data:" + deviceId;
    }

    /**
     * Số lượng tải lên OTA
     */
    public static String getOtaUploadCountKey(Long username) {
        return "ota:upload:count:" + username;
    }

    /**
     * Khóa bộ đệm sổ địa chỉ thiết bị
     */
    public static String getAddressBookKey() {
        return "device:address_book:all";
    }

}
